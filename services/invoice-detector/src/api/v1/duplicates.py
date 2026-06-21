"""
API Routes for managing duplicate pairs.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...auth.api_key import get_current_account
from ...db.session import get_db
from ...db.orm import DetectorInvoice, DuplicatePair
from ...db.models import DuplicateReviewAction

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


def _pair_to_dict(pair: DuplicatePair) -> dict:
    return {
        "id": str(pair.id),
        "account_id": pair.account_id,
        "invoice_a_id": str(pair.invoice_a_id),
        "invoice_b_id": str(pair.invoice_b_id),
        "similarity_score": float(pair.similarity_score) if pair.similarity_score is not None else None,
        "match_details": pair.match_details,
        "status": pair.status,
        "reviewed_by": pair.reviewed_by,
        "reviewed_at": pair.reviewed_at.isoformat() if pair.reviewed_at else None,
        "created_at": pair.created_at.isoformat() if pair.created_at else None,
    }


def _invoice_brief(inv: DetectorInvoice | None) -> dict | None:
    if inv is None:
        return None
    return {
        "id": str(inv.id),
        "filename": inv.filename,
        "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name,
        "total_amount": float(inv.total_amount) if inv.total_amount is not None else None,
        "invoice_date": inv.invoice_date,
    }


def _invoice_full(inv: DetectorInvoice | None) -> dict | None:
    if inv is None:
        return None
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


@router.get("/duplicates")
@limiter.limit("60/minute")
async def list_duplicates(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """List duplicate pairs with pagination and status filter."""
    offset = (page - 1) * limit

    base_filters = [DuplicatePair.account_id == account_id]
    if status:
        base_filters.append(DuplicatePair.status == status)

    total = db.scalar(
        select(func.count()).select_from(DuplicatePair).where(*base_filters)
    )

    pairs = db.scalars(
        select(DuplicatePair)
        .where(*base_filters)
        .order_by(DuplicatePair.similarity_score.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    # Enrich with invoice data
    enriched = []
    for pair in pairs:
        inv_a = db.get(DetectorInvoice, pair.invoice_a_id)
        inv_b = db.get(DetectorInvoice, pair.invoice_b_id)
        enriched.append({
            **_pair_to_dict(pair),
            "invoice_a": _invoice_brief(inv_a),
            "invoice_b": _invoice_brief(inv_b),
        })

    return {
        "data": enriched,
        "total": total or 0,
        "page": page,
        "limit": limit,
    }


@router.get("/duplicates/{duplicate_id}")
@limiter.limit("60/minute")
async def get_duplicate(
    request: Request,
    duplicate_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Get a single duplicate pair with full invoice details."""
    pair = db.scalars(
        select(DuplicatePair).where(
            DuplicatePair.id == uuid.UUID(duplicate_id),
            DuplicatePair.account_id == account_id,
        )
    ).first()

    if not pair:
        raise HTTPException(status_code=404, detail="Duplicate pair not found")

    # Get full invoice details
    inv_a = db.get(DetectorInvoice, pair.invoice_a_id)
    inv_b = db.get(DetectorInvoice, pair.invoice_b_id)

    return {
        "status": "ok",
        "data": {
            **_pair_to_dict(pair),
            "invoice_a": _invoice_full(inv_a),
            "invoice_b": _invoice_full(inv_b),
        },
    }


@router.patch("/duplicates/{duplicate_id}")
@limiter.limit("30/minute")
async def review_duplicate(
    request: Request,
    duplicate_id: str,
    data: DuplicateReviewAction,
    account_id: str = Depends(get_current_account),
    user_id: str = None,
    db: Session = Depends(get_db),
):
    """Review a duplicate pair (confirm or dismiss)."""
    pair = db.scalars(
        select(DuplicatePair).where(
            DuplicatePair.id == uuid.UUID(duplicate_id),
            DuplicatePair.account_id == account_id,
        )
    ).first()
    if not pair:
        raise HTTPException(status_code=404, detail="Duplicate pair not found")

    now = datetime.now(timezone.utc)
    pair.status = data.action
    pair.reviewed_at = now
    pair.reviewed_by = user_id or "api"
    db.commit()
    db.refresh(pair)

    return {"status": "ok", "data": _pair_to_dict(pair)}


@router.post("/duplicates/bulk-action")
@limiter.limit("10/minute")
async def bulk_action(
    request: Request,
    action: str = Query(..., pattern="^(confirmed|dismissed)$"),
    ids: list[str] = Query(...),
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Bulk confirm or dismiss duplicate pairs."""
    if len(ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 items per bulk action")

    now = datetime.now(timezone.utc)
    updated = 0

    for dup_id in ids:
        pair = db.scalars(
            select(DuplicatePair).where(
                DuplicatePair.id == uuid.UUID(dup_id),
                DuplicatePair.account_id == account_id,
                DuplicatePair.status == "pending",
            )
        ).first()
        if pair:
            pair.status = action
            pair.reviewed_at = now
            pair.reviewed_by = "bulk_api"
            updated += 1

    db.commit()

    return {"status": "ok", "updated": updated, "total_requested": len(ids)}


@router.get("/duplicates/stats")
@limiter.limit("30/minute")
async def duplicate_stats(
    request: Request,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Get duplicate detection statistics."""
    rows = db.execute(
        select(DuplicatePair.status, func.count())
        .where(DuplicatePair.account_id == account_id)
        .group_by(DuplicatePair.status)
    ).all()

    stats = {"total": 0, "pending": 0, "confirmed": 0, "dismissed": 0}
    for status_value, count in rows:
        stats["total"] += count
        if status_value in stats:
            stats[status_value] += count

    # Count invoices
    inv_count = db.scalar(
        select(func.count())
        .select_from(DetectorInvoice)
        .where(DetectorInvoice.account_id == account_id)
    )

    stats["total_invoices"] = inv_count or 0

    return {"status": "ok", "data": stats}
