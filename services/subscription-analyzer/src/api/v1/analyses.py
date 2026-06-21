from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, status, Header, Body, Request
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
import os
import uuid
import logging
from datetime import datetime, timezone
import io
import httpx

from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...auth.api_key import get_current_account
from ...config import settings
from ...db.session import SessionLocal, get_db
from ...db.orm import Analysis as AnalysisRow, AnalysisItem as AnalysisItemRow
from ...db.models import Analysis, AnalysisItem
from ...core.csv_parser import parse_csv
from ...core.pdf_parser import parse_pdf, is_pdf_supported, PDFParseError
from ...core.detector import detect_subscriptions
from ...core.pdf_generator import generate_pdf_report
from ...core.email_service import email_service

logger = logging.getLogger(__name__)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


class SendReportRequest(BaseModel):
    """Request model for sending report via email."""
    email: EmailStr
    include_pdf: bool = True
    recipient_name: Optional[str] = None

router = APIRouter()


def _analysis_to_dict(a: AnalysisRow) -> dict:
    """Serialize an Analysis row to a JSON-friendly dict (full record)."""
    return {
        "id": str(a.id),
        "account_id": str(a.account_id),
        "user_id": str(a.user_id),
        "status": a.status,
        "source_type": a.source_type,
        "filename": a.filename,
        "file_url": a.file_url,
        "total_transactions": a.total_transactions,
        "subscriptions_found": a.subscriptions_found,
        "potential_savings_eur": float(a.potential_savings_eur) if a.potential_savings_eur is not None else 0,
        "report_url": a.report_url,
        "error_message": a.error_message,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _item_to_dict(i: AnalysisItemRow) -> dict:
    """Serialize an AnalysisItem row to a JSON-friendly dict."""
    return {
        "id": str(i.id),
        "analysis_id": str(i.analysis_id),
        "merchant_descriptor": i.merchant_descriptor,
        "merchant_name": i.merchant_name,
        "category": i.category,
        "amount_avg": float(i.amount_avg) if i.amount_avg is not None else None,
        "amount_min": float(i.amount_min) if i.amount_min is not None else None,
        "amount_max": float(i.amount_max) if i.amount_max is not None else None,
        "currency": i.currency,
        "frequency": i.frequency,
        "occurrences": i.occurrences,
        "first_seen": i.first_seen.isoformat() if i.first_seen else None,
        "last_seen": i.last_seen.isoformat() if i.last_seen else None,
        "confidence_score": float(i.confidence_score) if i.confidence_score is not None else None,
        "is_subscription": i.is_subscription,
        "tags": i.tags if i.tags is not None else [],
        "recommendation": i.recommendation,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


async def run_analysis_task(analysis_id: str, account_id: str, file_content: bytes, source_type: str = "csv"):
    try:
        # Update status
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "processing"
                session.commit()

        # Parse based on source type
        if source_type == "pdf":
            try:
                transactions = parse_pdf(file_content)
            except PDFParseError as e:
                raise Exception(f"PDF parsing failed: {str(e)}")
        else:
            transactions = parse_csv(file_content)

        # Detect
        items = await detect_subscriptions(transactions, UUID(analysis_id))

        # Save Items
        with SessionLocal() as session:
            for item in items:
                data = item.model_dump(exclude={"id", "created_at"})
                session.add(AnalysisItemRow(**data))
            session.commit()

        # Calc stats
        total_tx = len(transactions)
        subs_found = len([i for i in items if i.is_subscription])
        savings = sum([i.amount_avg for i in items if i.is_subscription])

        # Update Analysis
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "completed"
                analysis.total_transactions = total_tx
                analysis.subscriptions_found = subs_found
                analysis.potential_savings_eur = savings
                analysis.completed_at = datetime.now(timezone.utc)
                session.commit()

    except Exception as e:
        print(f"Analysis failed: {e}")
        with SessionLocal() as session:
            analysis = session.get(AnalysisRow, UUID(analysis_id))
            if analysis:
                analysis.status = "failed"
                analysis.error_message = str(e)
                session.commit()

@router.post("/analyses", status_code=201)
async def create_analysis(
    file: UploadFile = File(...),
    account_id: str = Depends(get_current_account),
    user_id: str = Header("anonymous", alias="X-User-ID"),
    db: Session = Depends(get_db),
):
    # Determine file type
    filename = file.filename.lower()
    if filename.endswith('.pdf'):
        source_type = "pdf"
        # Check PDF support
        pdf_caps = is_pdf_supported()
        if not pdf_caps.get("text_extraction") and not pdf_caps.get("ocr_available"):
            raise HTTPException(
                400,
                "PDF support requires additional dependencies. Please use CSV format or contact support."
            )
    elif filename.endswith(('.csv', '.txt')):
        source_type = "csv"
    else:
        raise HTTPException(400, "Supported formats: CSV, TXT, PDF")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")

    # Store the uploaded file locally (private). We store the relative path.
    file_path = f"{account_id}/{uuid.uuid4()}_{file.filename}"
    try:
        abs_path = os.path.join(settings.UPLOAD_DIR, file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(content)
        # We DO NOT generate public URL for privacy. We store the path.
    except Exception as e:
        print(f"Storage upload error: {e}")
        raise HTTPException(500, "Failed to upload file")

    # Create Record
    analysis = AnalysisRow(
        account_id=UUID(account_id),
        user_id=UUID(user_id),
        status="pending",
        filename=file.filename,
        file_url=file_path,  # Storing path
        source_type=source_type,
    )
    db.add(analysis)
    db.commit()

    analysis_id = str(analysis.id)

    return {"analysis_id": analysis_id, "status": "pending", "source_type": source_type}

@router.post("/analyses/{analysis_id}/run")
async def run_analysis(
    analysis_id: str,
    background_tasks: BackgroundTasks,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    # Verify ownership
    analysis = db.scalars(
        select(AnalysisRow).where(
            AnalysisRow.id == UUID(analysis_id),
            AnalysisRow.account_id == UUID(account_id),
        )
    ).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found")

    if analysis.status == 'processing':
        return {"status": "processing", "message": "Already running"}

    # Atomic check-and-set: only update to 'processing' if still in expected state
    # This prevents race conditions when multiple requests try to start the same analysis
    update_count = db.query(AnalysisRow).filter(
        AnalysisRow.id == UUID(analysis_id),
        AnalysisRow.status.in_(["pending", "failed", "completed"]),
    ).update({AnalysisRow.status: "processing"}, synchronize_session=False)
    db.commit()
    if not update_count:
        return {"status": "processing", "message": "Already running"}

    # Download file content
    content = None
    try:
        path = analysis.file_url
        if not path:
             raise HTTPException(400, "No file associated")

        # Check if legacy public URL
        if path.startswith("http"):
             async with httpx.AsyncClient() as client:
                resp = await client.get(path)
                if resp.status_code == 200:
                    content = resp.content
                else:
                    raise HTTPException(400, "Could not retrieve file content")
        else:
            # Read from local storage using path
            abs_path = os.path.join(settings.UPLOAD_DIR, path)
            with open(abs_path, "rb") as f:
                content = f.read()

    except Exception as e:
        print(f"Download error: {e}")
        raise HTTPException(400, "Could not retrieve file content")

    source_type = analysis.source_type or 'csv'
    background_tasks.add_task(run_analysis_task, analysis_id, account_id, content, source_type)

    return {"status": "processing", "message": "Analysis started", "source_type": source_type}

@router.get("/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    analysis = db.scalars(
        select(AnalysisRow).where(
            AnalysisRow.id == UUID(analysis_id),
            AnalysisRow.account_id == UUID(account_id),
        )
    ).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found")

    # Get items
    items = db.scalars(
        select(AnalysisItemRow).where(AnalysisItemRow.analysis_id == UUID(analysis_id))
    ).all()

    return {**_analysis_to_dict(analysis), "items": [_item_to_dict(i) for i in items]}

@router.get("/analyses")
async def list_analyses(
    page: int = 1,
    limit: int = 20,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

    total = db.scalar(
        select(func.count()).select_from(AnalysisRow).where(
            AnalysisRow.account_id == UUID(account_id)
        )
    )

    rows = db.scalars(
        select(AnalysisRow)
        .where(AnalysisRow.account_id == UUID(account_id))
        .order_by(AnalysisRow.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "data": [_analysis_to_dict(r) for r in rows],
        "total": total or 0,
        "page": page
    }

@router.get("/analyses/{analysis_id}/report")
async def get_report(
    analysis_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    # Fetch analysis and items
    analysis_row = db.scalars(
        select(AnalysisRow).where(
            AnalysisRow.id == UUID(analysis_id),
            AnalysisRow.account_id == UUID(account_id),
        )
    ).first()
    if not analysis_row:
        raise HTTPException(404, "Analysis not found")

    analysis = Analysis(**_analysis_to_dict(analysis_row))

    item_rows = db.scalars(
        select(AnalysisItemRow).where(AnalysisItemRow.analysis_id == UUID(analysis_id))
    ).all()
    items = [AnalysisItem(**_item_to_dict(i)) for i in item_rows]

    pdf_bytes = generate_pdf_report(analysis, items)

    # Store report locally (Private). Store path, not public URL.
    report_path = f"{account_id}/{analysis_id}.pdf"
    try:
        abs_report = os.path.join(settings.REPORTS_DIR, report_path)
        os.makedirs(os.path.dirname(abs_report), exist_ok=True)
        with open(abs_report, "wb") as f:
            f.write(pdf_bytes)
        analysis_row.report_url = report_path
        db.commit()
    except Exception as e:
        print(f"Report upload error: {e}")
        # Continue to return bytes

    # Return Content directly (Secure)
    from fastapi.responses import Response
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/analyses/{analysis_id}/send-report")
async def send_report_email(
    analysis_id: str,
    request: SendReportRequest,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """
    Send analysis report to specified email address.

    - **email**: Recipient email address
    - **include_pdf**: Whether to attach PDF report (default: True)
    - **recipient_name**: Optional name for personalization
    """
    # Check if email service is configured
    if not email_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Please set SMTP credentials."
        )

    # Verify ownership and get analysis
    analysis_row = db.scalars(
        select(AnalysisRow).where(
            AnalysisRow.id == UUID(analysis_id),
            AnalysisRow.account_id == UUID(account_id),
        )
    ).first()
    if not analysis_row:
        raise HTTPException(404, "Analysis not found")

    # Check if analysis is completed
    if analysis_row.status != "completed":
        raise HTTPException(400, "Analysis must be completed before sending report")

    analysis = Analysis(**_analysis_to_dict(analysis_row))

    # Get analysis items
    item_rows = db.scalars(
        select(AnalysisItemRow).where(AnalysisItemRow.analysis_id == UUID(analysis_id))
    ).all()
    items = [AnalysisItem(**_item_to_dict(i)) for i in item_rows]

    # Generate PDF if requested
    pdf_bytes = None
    if request.include_pdf:
        pdf_bytes = generate_pdf_report(analysis, items)

    # Send email
    result = await email_service.send_report_email(
        recipient_email=request.email,
        analysis=analysis,
        items=items,
        pdf_bytes=pdf_bytes,
        recipient_name=request.recipient_name
    )

    if not result["success"]:
        raise HTTPException(500, result["message"])

    return {
        "message": result["message"],
        "recipient": request.email,
        "pdf_attached": request.include_pdf
    }


@router.get("/email/status")
async def get_email_status(
    account_id: str = Depends(get_current_account)
):
    """Check if email service is properly configured."""
    return {
        "configured": email_service.is_configured(),
        "smtp_host": email_service.host if email_service.is_configured() else "not_configured",
        "sender_email": email_service.sender_email if email_service.is_configured() else "not_configured"
    }


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    # 1. Fetch analysis to get file paths
    analysis = db.scalars(
        select(AnalysisRow).where(
            AnalysisRow.id == UUID(analysis_id),
            AnalysisRow.account_id == UUID(account_id),
        )
    ).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found")

    file_url = analysis.file_url
    report_url = analysis.report_url

    # 2. Delete related items
    db.query(AnalysisItemRow).filter(
        AnalysisItemRow.analysis_id == UUID(analysis_id)
    ).delete(synchronize_session=False)

    # 3. Delete files from local storage (Files & Reports)
    try:
        if file_url and not file_url.startswith('http'):
            abs_upload = os.path.join(settings.UPLOAD_DIR, file_url)
            if os.path.exists(abs_upload):
                os.remove(abs_upload)

        if report_url:
            abs_report = os.path.join(settings.REPORTS_DIR, report_url)
            if os.path.exists(abs_report):
                os.remove(abs_report)
    except Exception as e:
        print(f"Warning: Failed to cleanup storage files: {e}")

    # 4. Delete Analysis record
    db.delete(analysis)
    db.commit()

    return {"message": "Analysis deleted successfully"}


@router.get("/capabilities")
async def get_capabilities():
    """
    Get service capabilities including PDF/OCR support status.
    Useful for frontend to determine which file types are accepted.
    """
    pdf_caps = is_pdf_supported()
    email_configured = email_service.is_configured()

    return {
        "supported_formats": ["csv", "txt"] + (["pdf"] if pdf_caps.get("text_extraction") or pdf_caps.get("ocr_available") else []),
        "pdf_support": {
            "available": pdf_caps.get("text_extraction") or pdf_caps.get("ocr_available"),
            "text_extraction": pdf_caps.get("text_extraction", False),
            "ocr_available": pdf_caps.get("ocr_available", False),
            "ocr_languages": pdf_caps.get("ocr_languages"),
        },
        "email_support": {
            "available": email_configured,
        },
        "max_file_size_mb": 10
    }
