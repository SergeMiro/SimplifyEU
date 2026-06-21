"""
Celery tasks for subscription analysis.

These tasks run in background workers, allowing the API to respond immediately
while heavy processing happens asynchronously.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="src.tasks.analysis_tasks.run_analysis",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_analysis(
    self,
    analysis_id: str,
    account_id: str,
    file_content_base64: str,
    source_type: str = "csv"
) -> dict:
    """
    Run subscription analysis in background.

    Args:
        analysis_id: UUID of the analysis record
        account_id: Account ID for the analysis
        file_content_base64: Base64 encoded file content
        source_type: 'csv' or 'pdf'

    Returns:
        dict with analysis results summary
    """
    import base64
    from ..db.session import SessionLocal
    from ..db.orm import Analysis as AnalysisRow, AnalysisItem as AnalysisItemRow
    from ..core.csv_parser import parse_csv
    from ..core.pdf_parser import parse_pdf, PDFParseError
    from ..core.detector import detect_subscriptions

    logger.info(f"[CELERY] Starting analysis {analysis_id} for account {account_id}")

    try:
        # Update status to processing
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "processing"
                session.commit()

        # Decode file content
        file_content = base64.b64decode(file_content_base64)

        # Parse based on source type
        if source_type == "pdf":
            try:
                transactions = parse_pdf(file_content)
            except PDFParseError as e:
                raise Exception(f"PDF parsing failed: {str(e)}")
        else:
            transactions = parse_csv(file_content)

        logger.info(f"[CELERY] Parsed {len(transactions)} transactions")

        # Detect subscriptions (async call needs to be run in sync context)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            items = loop.run_until_complete(
                detect_subscriptions(transactions, UUID(analysis_id))
            )
        finally:
            loop.close()

        # Save items to database
        with SessionLocal() as session:
            for item in items:
                data = item.model_dump(exclude={"id", "created_at"})
                session.add(AnalysisItemRow(**data))
            session.commit()

        # Calculate stats
        total_tx = len(transactions)
        subs_found = len([i for i in items if i.is_subscription])
        savings = sum([i.amount_avg for i in items if i.is_subscription])

        # Update analysis with results
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "completed"
                analysis.total_transactions = total_tx
                analysis.subscriptions_found = subs_found
                analysis.potential_savings_eur = savings
                analysis.completed_at = datetime.now(timezone.utc)
                session.commit()

        logger.info(f"[CELERY] Analysis {analysis_id} completed: {subs_found} subscriptions found")

        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "total_transactions": total_tx,
            "subscriptions_found": subs_found,
            "potential_savings": savings
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[CELERY] Analysis {analysis_id} timed out")
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "failed"
                analysis.error_message = "Analysis timed out after 9 minutes"
                session.commit()
        raise

    except Exception as e:
        logger.error(f"[CELERY] Analysis {analysis_id} failed: {e}")
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "failed"
                analysis.error_message = str(e)[:500]  # Limit error message length
                session.commit()
        raise


@shared_task(
    bind=True,
    name="src.tasks.analysis_tasks.send_email_report",
    max_retries=3,
    default_retry_delay=120,
)
def send_email_report(
    self,
    analysis_id: str,
    email: str,
    include_pdf: bool = True,
    recipient_name: Optional[str] = None
) -> dict:
    """
    Send analysis report via email in background.

    Args:
        analysis_id: UUID of the completed analysis
        email: Recipient email address
        include_pdf: Whether to include PDF attachment
        recipient_name: Optional name for personalization

    Returns:
        dict with send status
    """
    from ..db.session import SessionLocal
    from ..db.orm import Analysis as AnalysisRow, AnalysisItem as AnalysisItemRow
    from ..db.models import Analysis as AnalysisModel, AnalysisItem
    from ..core.email_service import email_service
    from ..core.pdf_generator import generate_pdf_report

    logger.info(f"[CELERY] Sending email report for analysis {analysis_id} to {email}")

    try:
        # Fetch analysis data and items
        with SessionLocal() as session:
            analysis_row = session.get(AnalysisRow, UUID(analysis_id))

            if not analysis_row:
                raise Exception(f"Analysis {analysis_id} not found")

            if analysis_row.status != "completed":
                raise Exception(f"Analysis is not completed: {analysis_row.status}")

            analysis_obj = AnalysisModel.model_validate(analysis_row, from_attributes=True)

            item_rows = session.scalars(
                select(AnalysisItemRow).where(
                    AnalysisItemRow.analysis_id == UUID(analysis_id)
                )
            ).all()
            item_objs = [
                AnalysisItem.model_validate(i, from_attributes=True) for i in item_rows
            ]

        # Generate PDF if requested
        pdf_bytes = None
        if include_pdf:
            pdf_bytes = generate_pdf_report(analysis_obj, item_objs)

        # Send email
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(email_service.send_report_email(
                recipient_email=email,
                analysis=analysis_obj,
                items=item_objs,
                pdf_bytes=pdf_bytes,
                recipient_name=recipient_name,
            ))
            success = result.get("success", False)
        finally:
            loop.close()

        if not success:
            raise Exception("Email sending failed")

        logger.info(f"[CELERY] Email sent successfully to {email}")

        return {
            "analysis_id": analysis_id,
            "email": email,
            "status": "sent",
            "include_pdf": include_pdf
        }

    except Exception as e:
        logger.error(f"[CELERY] Email sending failed for {analysis_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e)


@shared_task(name="src.tasks.analysis_tasks.cleanup_old_analyses")
def cleanup_old_analyses(days_old: int = 30) -> dict:
    """
    Cleanup old analyses and their associated data.
    Runs daily via Celery beat.

    Args:
        days_old: Delete analyses older than this many days

    Returns:
        dict with cleanup stats
    """
    from datetime import timedelta
    from ..db.session import SessionLocal
    from ..db.orm import Analysis as AnalysisRow, AnalysisItem as AnalysisItemRow

    logger.info(f"[CELERY] Starting cleanup of analyses older than {days_old} days")

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        with SessionLocal() as session:
            # Get old analyses
            old_ids = session.scalars(
                select(AnalysisRow.id).where(AnalysisRow.created_at < cutoff_date)
            ).all()

            deleted_count = 0
            for analysis_id in old_ids:
                # Delete items first (foreign key constraint)
                session.query(AnalysisItemRow).filter(
                    AnalysisItemRow.analysis_id == analysis_id
                ).delete(synchronize_session=False)

                # Delete analysis
                session.query(AnalysisRow).filter(
                    AnalysisRow.id == analysis_id
                ).delete(synchronize_session=False)

                deleted_count += 1

            session.commit()

        logger.info(f"[CELERY] Cleanup completed: deleted {deleted_count} old analyses")

        return {
            "deleted_analyses": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"[CELERY] Cleanup failed: {e}")
        raise
