"""
Celery tasks for subscription analysis.

These tasks run in background workers, allowing the API to respond immediately
while heavy processing happens asynchronously.
"""
import logging
from datetime import datetime
from uuid import UUID
from typing import Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

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
    from ..db.client import supabase
    from ..core.csv_parser import parse_csv
    from ..core.pdf_parser import parse_pdf, PDFParseError
    from ..core.detector import detect_subscriptions
    
    logger.info(f"[CELERY] Starting analysis {analysis_id} for account {account_id}")
    
    try:
        # Update status to processing
        supabase.table("analyses").update({
            "status": "processing"
        }).eq("id", analysis_id).execute()
        
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
        items_data = []
        for item in items:
            data = item.model_dump(exclude={"id", "created_at"})
            data['analysis_id'] = str(data['analysis_id'])
            data['first_seen'] = data['first_seen'].isoformat()
            data['last_seen'] = data['last_seen'].isoformat()
            items_data.append(data)
        
        if items_data:
            supabase.table("analysis_items").insert(items_data).execute()
        
        # Calculate stats
        total_tx = len(transactions)
        subs_found = len([i for i in items if i.is_subscription])
        savings = sum([i.amount_avg for i in items if i.is_subscription])
        
        # Update analysis with results
        supabase.table("analyses").update({
            "status": "completed",
            "total_transactions": total_tx,
            "subscriptions_found": subs_found,
            "potential_savings_eur": savings,
            "completed_at": datetime.now().isoformat()
        }).eq("id", analysis_id).execute()
        
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
        supabase.table("analyses").update({
            "status": "failed",
            "error_message": "Analysis timed out after 9 minutes"
        }).eq("id", analysis_id).execute()
        raise
        
    except Exception as e:
        logger.error(f"[CELERY] Analysis {analysis_id} failed: {e}")
        supabase.table("analyses").update({
            "status": "failed",
            "error_message": str(e)[:500]  # Limit error message length
        }).eq("id", analysis_id).execute()
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
    from ..db.client import supabase
    from ..core.email_service import email_service
    from ..core.pdf_generator import generate_pdf_report
    
    logger.info(f"[CELERY] Sending email report for analysis {analysis_id} to {email}")
    
    try:
        # Fetch analysis data
        analysis_res = supabase.table("analyses").select("*").eq("id", analysis_id).single().execute()
        analysis = analysis_res.data
        
        if not analysis:
            raise Exception(f"Analysis {analysis_id} not found")
        
        if analysis["status"] != "completed":
            raise Exception(f"Analysis is not completed: {analysis['status']}")
        
        # Fetch items
        items_res = supabase.table("analysis_items").select("*").eq("analysis_id", analysis_id).execute()
        items = items_res.data
        
        # Generate PDF if requested
        pdf_bytes = None
        if include_pdf:
            # Convert items for PDF generator
            from ..db.models import AnalysisItem
            from uuid import UUID
            from datetime import datetime
            
            item_models = []
            for item in items:
                item_models.append(AnalysisItem(
                    id=UUID(item["id"]) if item.get("id") else None,
                    analysis_id=UUID(item["analysis_id"]),
                    description=item["description"],
                    amount_avg=item["amount_avg"],
                    currency=item["currency"],
                    frequency=item["frequency"],
                    occurrence_count=item["occurrence_count"],
                    confidence_score=item["confidence_score"],
                    first_seen=datetime.fromisoformat(item["first_seen"]),
                    last_seen=datetime.fromisoformat(item["last_seen"]),
                    is_subscription=item["is_subscription"],
                    category=item.get("category"),
                ))
            
            pdf_bytes = generate_pdf_report(item_models, UUID(analysis_id))
        
        # Send email
        success = email_service.send_subscription_report(
            to_email=email,
            recipient_name=recipient_name or "User",
            items=items,
            analysis_id=analysis_id,
            pdf_report=pdf_bytes
        )
        
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
    from ..db.client import supabase
    
    logger.info(f"[CELERY] Starting cleanup of analyses older than {days_old} days")
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        # Get old analyses
        old_analyses = supabase.table("analyses").select("id").lt("created_at", cutoff_date).execute()
        
        deleted_count = 0
        for analysis in old_analyses.data:
            analysis_id = analysis["id"]
            
            # Delete items first (foreign key constraint)
            supabase.table("analysis_items").delete().eq("analysis_id", analysis_id).execute()
            
            # Delete analysis
            supabase.table("analyses").delete().eq("id", analysis_id).execute()
            
            deleted_count += 1
        
        logger.info(f"[CELERY] Cleanup completed: deleted {deleted_count} old analyses")
        
        return {
            "deleted_analyses": deleted_count,
            "cutoff_date": cutoff_date
        }
        
    except Exception as e:
        logger.error(f"[CELERY] Cleanup failed: {e}")
        raise
