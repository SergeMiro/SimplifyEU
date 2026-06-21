"""
API Routes for Invoice upload, processing, and listing.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ...auth.api_key import get_current_account
from ...config import settings
from ...db.session import SessionLocal, get_db
from ...db.orm import DetectorInvoice, DuplicatePair
from ...core.pdf_extractor import extract_text_from_pdf, compute_file_hash, validate_file_magic
from ...core.ocr_processor import ocr_image
from ...core.invoice_parser import parse_invoice_text
from ...core.similarity import compute_similarity_score

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


def _invoice_to_dict(inv: DetectorInvoice) -> dict:
    """Serialize a DetectorInvoice row to a JSON-friendly dict (full record)."""
    return {
        "id": str(inv.id),
        "account_id": inv.account_id,
        "filename": inv.filename,
        "file_hash": inv.file_hash,
        "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "total_amount": float(inv.total_amount) if inv.total_amount is not None else None,
        "currency": inv.currency,
        "line_items": inv.line_items,
        "raw_text": inv.raw_text,
        "ocr_used": inv.ocr_used,
        "status": inv.status,
        "processing_error": inv.processing_error,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def _invoice_summary(inv: DetectorInvoice) -> dict:
    """Compact list view of a DetectorInvoice row."""
    return {
        "id": str(inv.id),
        "filename": inv.filename,
        "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name,
        "total_amount": float(inv.total_amount) if inv.total_amount is not None else None,
        "currency": inv.currency,
        "invoice_date": inv.invoice_date,
        "status": inv.status,
        "ocr_used": inv.ocr_used,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


@router.post("/invoices/upload", status_code=201)
@limiter.limit("20/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Upload an invoice file (PDF or image) for processing."""
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Save to temp directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    invoice_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{invoice_id}{ext}")

    with open(file_path, "wb") as f:
        f.write(content)

    # Validate magic bytes
    if not validate_file_magic(file_path):
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail="File content does not match expected format (magic bytes check failed)",
        )

    # Compute file hash
    file_hash = compute_file_hash(file_path)

    # Check for exact file duplicate (same hash)
    existing = db.scalars(
        select(DetectorInvoice)
        .where(
            DetectorInvoice.account_id == account_id,
            DetectorInvoice.file_hash == file_hash,
        )
    ).first()

    if existing:
        os.remove(file_path)
        return {
            "status": "duplicate",
            "message": "Exact duplicate file already uploaded",
            "existing_invoice_id": str(existing.id),
        }

    # Create invoice record
    invoice = DetectorInvoice(
        id=uuid.UUID(invoice_id),
        account_id=account_id,
        filename=file.filename,
        file_hash=file_hash,
        status="pending",
        ocr_used=False,
    )
    db.add(invoice)
    db.commit()

    # Process in background
    background_tasks.add_task(_process_invoice, invoice_id, file_path, account_id, ext)

    return {
        "status": "ok",
        "data": {"id": invoice_id, "filename": file.filename, "status": "pending"},
    }


async def _process_invoice(invoice_id: str, file_path: str, account_id: str, ext: str):
    """Background task: extract text, parse, and find duplicates.

    Runs outside the request lifecycle, so it opens its own SQLAlchemy session.
    """
    try:
        raw_text = None
        ocr_used = False

        # Try PDF text extraction
        if ext == ".pdf":
            raw_text = extract_text_from_pdf(file_path)

        # Fall back to OCR for images or if PDF had no text
        if not raw_text and ext in (".png", ".jpg", ".jpeg", ".tiff"):
            raw_text = ocr_image(file_path)
            ocr_used = True
        elif not raw_text and ext == ".pdf":
            # Scanned PDF — try OCR on the file as an image
            raw_text = ocr_image(file_path)
            ocr_used = True

        if not raw_text:
            with SessionLocal() as session:
                inv = session.get(DetectorInvoice, uuid.UUID(invoice_id))
                if inv:
                    inv.status = "error"
                    inv.processing_error = "Could not extract text from document"
                    inv.updated_at = datetime.now(timezone.utc)
                    session.commit()
            return

        # Parse extracted text
        parsed = parse_invoice_text(raw_text)

        # Update invoice with parsed data
        with SessionLocal() as session:
            inv = session.get(DetectorInvoice, uuid.UUID(invoice_id))
            if inv:
                inv.invoice_number = parsed.invoice_number
                inv.vendor_name = parsed.vendor_name
                inv.invoice_date = parsed.invoice_date
                inv.due_date = parsed.due_date
                inv.total_amount = parsed.total_amount
                inv.currency = parsed.currency
                inv.line_items = parsed.line_items
                inv.raw_text = raw_text[:10000]  # Truncate for storage
                inv.ocr_used = ocr_used
                inv.status = "processed"
                inv.updated_at = datetime.now(timezone.utc)
                session.commit()

        # Find potential duplicates
        await _find_duplicates(invoice_id, account_id)

    except Exception as e:
        logger.error(f"Processing failed for invoice {invoice_id}: {e}")
        with SessionLocal() as session:
            inv = session.get(DetectorInvoice, uuid.UUID(invoice_id))
            if inv:
                inv.status = "error"
                inv.processing_error = str(e)[:500]
                inv.updated_at = datetime.now(timezone.utc)
                session.commit()
    finally:
        # Clean up temp file
        Path(file_path).unlink(missing_ok=True)


async def _find_duplicates(invoice_id: str, account_id: str):
    """Compare the new invoice against all existing ones for the same account."""
    with SessionLocal() as session:
        # Get the new invoice
        new_inv = session.get(DetectorInvoice, uuid.UUID(invoice_id))
        if not new_inv:
            return

        new_data = _invoice_to_dict(new_inv)

        # Get all other processed invoices
        existing = session.scalars(
            select(DetectorInvoice)
            .where(
                DetectorInvoice.account_id == account_id,
                DetectorInvoice.status == "processed",
                DetectorInvoice.id != uuid.UUID(invoice_id),
            )
            .limit(500)
        ).all()

        if not existing:
            return

        for old_inv in existing:
            old_data = _invoice_to_dict(old_inv)
            result = compute_similarity_score(new_data, old_data)

            if result["is_duplicate"]:
                dup = DuplicatePair(
                    account_id=account_id,
                    invoice_a_id=uuid.UUID(invoice_id),
                    invoice_b_id=old_inv.id,
                    similarity_score=result["total_score"],
                    match_details=result["field_scores"],
                    status="pending",
                )
                session.add(dup)
                logger.info(
                    f"Duplicate found: {invoice_id} ↔ {old_inv.id} "
                    f"(score={result['total_score']:.4f})"
                )

        session.commit()


@router.get("/invoices")
@limiter.limit("60/minute")
async def list_invoices(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """List invoices with pagination."""
    offset = (page - 1) * limit

    base_filters = [DetectorInvoice.account_id == account_id]
    if status:
        base_filters.append(DetectorInvoice.status == status)

    total = db.scalar(
        select(func.count()).select_from(DetectorInvoice).where(*base_filters)
    )

    rows = db.scalars(
        select(DetectorInvoice)
        .where(*base_filters)
        .order_by(DetectorInvoice.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "data": [_invoice_summary(r) for r in rows],
        "total": total or 0,
        "page": page,
        "limit": limit,
    }


@router.get("/invoices/{invoice_id}")
@limiter.limit("60/minute")
async def get_invoice(
    request: Request,
    invoice_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Get a single invoice by ID."""
    inv = db.scalars(
        select(DetectorInvoice).where(
            DetectorInvoice.id == uuid.UUID(invoice_id),
            DetectorInvoice.account_id == account_id,
        )
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {"status": "ok", "data": _invoice_to_dict(inv)}


@router.delete("/invoices/{invoice_id}")
@limiter.limit("20/minute")
async def delete_invoice(
    request: Request,
    invoice_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Delete an invoice and its duplicate pairs."""
    inv = db.scalars(
        select(DetectorInvoice).where(
            DetectorInvoice.id == uuid.UUID(invoice_id),
            DetectorInvoice.account_id == account_id,
        )
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv_uuid = uuid.UUID(invoice_id)

    # Delete duplicate pairs referencing this invoice
    dup_pairs = db.scalars(
        select(DuplicatePair).where(
            or_(
                DuplicatePair.invoice_a_id == inv_uuid,
                DuplicatePair.invoice_b_id == inv_uuid,
            )
        )
    ).all()
    for pair in dup_pairs:
        db.delete(pair)

    db.delete(inv)
    db.commit()

    return {"status": "ok", "message": "Invoice deleted"}
