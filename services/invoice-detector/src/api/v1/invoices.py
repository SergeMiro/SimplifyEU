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

from ...auth.api_key import get_current_account
from ...config import settings
from ...db.client import supabase
from ...core.pdf_extractor import extract_text_from_pdf, compute_file_hash, validate_file_magic
from ...core.ocr_processor import ocr_image
from ...core.invoice_parser import parse_invoice_text
from ...core.similarity import compute_similarity_score

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.post("/invoices/upload", status_code=201)
@limiter.limit("20/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    account_id: str = Depends(get_current_account),
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
    existing = (
        supabase.table("invoices")
        .select("id, filename")
        .eq("account_id", account_id)
        .eq("file_hash", file_hash)
        .execute()
    )

    if existing.data:
        os.remove(file_path)
        return {
            "status": "duplicate",
            "message": "Exact duplicate file already uploaded",
            "existing_invoice_id": existing.data[0]["id"],
        }

    # Create invoice record
    now = datetime.now(timezone.utc)
    record = {
        "id": invoice_id,
        "account_id": account_id,
        "filename": file.filename,
        "file_hash": file_hash,
        "status": "pending",
        "ocr_used": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    supabase.table("invoices").insert(record).execute()

    # Process in background
    background_tasks.add_task(_process_invoice, invoice_id, file_path, account_id, ext)

    return {
        "status": "ok",
        "data": {"id": invoice_id, "filename": file.filename, "status": "pending"},
    }


async def _process_invoice(invoice_id: str, file_path: str, account_id: str, ext: str):
    """Background task: extract text, parse, and find duplicates."""
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
            supabase.table("invoices").update({
                "status": "error",
                "processing_error": "Could not extract text from document",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", invoice_id).execute()
            return

        # Parse extracted text
        parsed = parse_invoice_text(raw_text)

        # Update invoice with parsed data
        supabase.table("invoices").update({
            "invoice_number": parsed.invoice_number,
            "vendor_name": parsed.vendor_name,
            "invoice_date": parsed.invoice_date,
            "due_date": parsed.due_date,
            "total_amount": parsed.total_amount,
            "currency": parsed.currency,
            "line_items": parsed.line_items,
            "raw_text": raw_text[:10000],  # Truncate for storage
            "ocr_used": ocr_used,
            "status": "processed",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", invoice_id).execute()

        # Find potential duplicates
        await _find_duplicates(invoice_id, account_id)

    except Exception as e:
        logger.error(f"Processing failed for invoice {invoice_id}: {e}")
        supabase.table("invoices").update({
            "status": "error",
            "processing_error": str(e)[:500],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", invoice_id).execute()
    finally:
        # Clean up temp file
        Path(file_path).unlink(missing_ok=True)


async def _find_duplicates(invoice_id: str, account_id: str):
    """Compare the new invoice against all existing ones for the same account."""
    # Get the new invoice
    new_inv = (
        supabase.table("invoices")
        .select("*")
        .eq("id", invoice_id)
        .single()
        .execute()
    )
    if not new_inv.data:
        return

    new_data = new_inv.data

    # Get all other processed invoices
    existing = (
        supabase.table("invoices")
        .select("*")
        .eq("account_id", account_id)
        .eq("status", "processed")
        .neq("id", invoice_id)
        .limit(500)
        .execute()
    )

    if not existing.data:
        return

    for old_inv in existing.data:
        result = compute_similarity_score(new_data, old_inv)

        if result["is_duplicate"]:
            dup_record = {
                "id": str(uuid.uuid4()),
                "account_id": account_id,
                "invoice_a_id": invoice_id,
                "invoice_b_id": old_inv["id"],
                "similarity_score": result["total_score"],
                "match_details": result["field_scores"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            supabase.table("duplicate_pairs").insert(dup_record).execute()
            logger.info(
                f"Duplicate found: {invoice_id} ↔ {old_inv['id']} "
                f"(score={result['total_score']:.4f})"
            )


@router.get("/invoices")
@limiter.limit("60/minute")
async def list_invoices(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    account_id: str = Depends(get_current_account),
):
    """List invoices with pagination."""
    offset = (page - 1) * limit

    query = (
        supabase.table("invoices")
        .select("id, filename, invoice_number, vendor_name, total_amount, "
                "currency, invoice_date, status, ocr_used, created_at",
                count="exact")
        .eq("account_id", account_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()

    return {
        "data": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }


@router.get("/invoices/{invoice_id}")
@limiter.limit("60/minute")
async def get_invoice(
    request: Request,
    invoice_id: str,
    account_id: str = Depends(get_current_account),
):
    """Get a single invoice by ID."""
    result = (
        supabase.table("invoices")
        .select("*")
        .eq("id", invoice_id)
        .eq("account_id", account_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {"status": "ok", "data": result.data[0]}


@router.delete("/invoices/{invoice_id}")
@limiter.limit("20/minute")
async def delete_invoice(
    request: Request,
    invoice_id: str,
    account_id: str = Depends(get_current_account),
):
    """Delete an invoice and its duplicate pairs."""
    result = (
        supabase.table("invoices")
        .select("id")
        .eq("id", invoice_id)
        .eq("account_id", account_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Delete duplicate pairs referencing this invoice
    supabase.table("duplicate_pairs").delete().or_(
        f"invoice_a_id.eq.{invoice_id},invoice_b_id.eq.{invoice_id}"
    ).execute()

    supabase.table("invoices").delete().eq("id", invoice_id).execute()

    return {"status": "ok", "message": "Invoice deleted"}
