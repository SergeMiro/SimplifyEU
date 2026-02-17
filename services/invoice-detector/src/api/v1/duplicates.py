"""
API Routes for managing duplicate pairs.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address

from ...auth.api_key import get_current_account
from ...db.client import supabase
from ...db.models import DuplicateReviewAction

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/duplicates")
@limiter.limit("60/minute")
async def list_duplicates(
    request: Request,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    account_id: str = Depends(get_current_account),
):
    """List duplicate pairs with pagination and status filter."""
    offset = (page - 1) * limit

    query = (
        supabase.table("duplicate_pairs")
        .select("*", count="exact")
        .eq("account_id", account_id)
        .order("similarity_score", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()

    # Enrich with invoice data
    enriched = []
    for pair in (result.data or []):
        inv_a = (
            supabase.table("invoices")
            .select("id, filename, invoice_number, vendor_name, total_amount, invoice_date")
            .eq("id", pair.get("invoice_a_id"))
            .execute()
        )
        inv_b = (
            supabase.table("invoices")
            .select("id, filename, invoice_number, vendor_name, total_amount, invoice_date")
            .eq("id", pair.get("invoice_b_id"))
            .execute()
        )

        enriched.append({
            **pair,
            "invoice_a": inv_a.data[0] if inv_a.data else None,
            "invoice_b": inv_b.data[0] if inv_b.data else None,
        })

    return {
        "data": enriched,
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }


@router.get("/duplicates/{duplicate_id}")
@limiter.limit("60/minute")
async def get_duplicate(
    request: Request,
    duplicate_id: str,
    account_id: str = Depends(get_current_account),
):
    """Get a single duplicate pair with full invoice details."""
    result = (
        supabase.table("duplicate_pairs")
        .select("*")
        .eq("id", duplicate_id)
        .eq("account_id", account_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Duplicate pair not found")

    pair = result.data[0]

    # Get full invoice details
    inv_a = supabase.table("invoices").select("*").eq("id", pair["invoice_a_id"]).execute()
    inv_b = supabase.table("invoices").select("*").eq("id", pair["invoice_b_id"]).execute()

    return {
        "status": "ok",
        "data": {
            **pair,
            "invoice_a": inv_a.data[0] if inv_a.data else None,
            "invoice_b": inv_b.data[0] if inv_b.data else None,
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
):
    """Review a duplicate pair (confirm or dismiss)."""
    existing = (
        supabase.table("duplicate_pairs")
        .select("id")
        .eq("id", duplicate_id)
        .eq("account_id", account_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Duplicate pair not found")

    now = datetime.now(timezone.utc)
    update = {
        "status": data.action,
        "reviewed_at": now.isoformat(),
        "reviewed_by": user_id or "api",
    }

    result = (
        supabase.table("duplicate_pairs")
        .update(update)
        .eq("id", duplicate_id)
        .execute()
    )

    return {"status": "ok", "data": result.data[0] if result.data else update}


@router.post("/duplicates/bulk-action")
@limiter.limit("10/minute")
async def bulk_action(
    request: Request,
    action: str = Query(..., pattern="^(confirmed|dismissed)$"),
    ids: list[str] = Query(...),
    account_id: str = Depends(get_current_account),
):
    """Bulk confirm or dismiss duplicate pairs."""
    if len(ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 items per bulk action")

    now = datetime.now(timezone.utc)
    updated = 0

    for dup_id in ids:
        res = (
            supabase.table("duplicate_pairs")
            .update({
                "status": action,
                "reviewed_at": now.isoformat(),
                "reviewed_by": "bulk_api",
            })
            .eq("id", dup_id)
            .eq("account_id", account_id)
            .eq("status", "pending")
            .execute()
        )
        if res.data:
            updated += 1

    return {"status": "ok", "updated": updated, "total_requested": len(ids)}


@router.get("/duplicates/stats")
@limiter.limit("30/minute")
async def duplicate_stats(
    request: Request,
    account_id: str = Depends(get_current_account),
):
    """Get duplicate detection statistics."""
    all_pairs = (
        supabase.table("duplicate_pairs")
        .select("status", count="exact")
        .eq("account_id", account_id)
        .execute()
    )

    stats = {"total": all_pairs.count or 0, "pending": 0, "confirmed": 0, "dismissed": 0}

    for pair in (all_pairs.data or []):
        s = pair.get("status", "")
        if s in stats:
            stats[s] += 1

    # Count invoices
    inv_count = (
        supabase.table("invoices")
        .select("id", count="exact")
        .eq("account_id", account_id)
        .execute()
    )

    stats["total_invoices"] = inv_count.count or 0

    return {"status": "ok", "data": stats}
