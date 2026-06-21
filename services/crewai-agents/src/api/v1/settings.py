"""
API endpoints for business profile and agent configuration.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...auth.api_key import get_current_account
from ...db.session import get_db
from ...db.orm import (
    BusinessProfile as BusinessProfileRow,
    TaxObligation as TaxObligationRow,
    FinancialInsight as FinancialInsightRow,
)
from ...db.models import BusinessProfile, BusinessType, TaxRegime, DeclarationFrequency

logger = logging.getLogger(__name__)
router = APIRouter()


def _business_profile_to_dict(p: BusinessProfileRow) -> dict:
    return {
        "id": str(p.id),
        "account_id": p.account_id,
        "business_type": p.business_type,
        "tax_regime": p.tax_regime,
        "declaration_frequency": p.declaration_frequency,
        "tva_applicable": p.tva_applicable,
        "siret": p.siret,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _tax_obligation_to_dict(o: TaxObligationRow) -> dict:
    return {
        "id": str(o.id),
        "account_id": o.account_id,
        "obligation_type": o.obligation_type,
        "title": o.title,
        "description": o.description,
        "deadline": o.deadline.isoformat() if o.deadline else None,
        "status": o.status,
        "draft_data": o.draft_data,
        "service_url": o.service_url,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


def _financial_insight_to_dict(i: FinancialInsightRow) -> dict:
    return {
        "id": str(i.id),
        "account_id": i.account_id,
        "insight_type": i.insight_type,
        "title": i.title,
        "description": i.description,
        "severity": i.severity,
        "data": i.data,
        "acknowledged": i.acknowledged,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


@router.get("/business-profile")
async def get_business_profile(
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Get the business profile for the current account."""
    try:
        row = db.scalars(
            select(BusinessProfileRow)
            .where(BusinessProfileRow.account_id == account_id)
            .limit(1)
        ).first()
        if row is not None:
            return _business_profile_to_dict(row)
        return {"message": "No business profile configured", "profile": None}
    except Exception as e:
        logger.error(f"Error fetching business profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch business profile")


@router.post("/business-profile")
async def create_or_update_business_profile(
    profile: BusinessProfile,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Create or update the business profile."""
    try:
        row = db.scalars(
            select(BusinessProfileRow)
            .where(BusinessProfileRow.account_id == account_id)
            .limit(1)
        ).first()

        data = {
            "business_type": profile.business_type.value,
            "tax_regime": profile.tax_regime.value,
            "declaration_frequency": profile.declaration_frequency.value,
            "tva_applicable": profile.tva_applicable,
        }
        if profile.siret:
            data["siret"] = profile.siret

        if row is not None:
            for field, value in data.items():
                setattr(row, field, value)
        else:
            row = BusinessProfileRow(account_id=account_id, **data)
            db.add(row)

        db.commit()
        db.refresh(row)
        return _business_profile_to_dict(row)
    except Exception as e:
        logger.error(f"Error saving business profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to save business profile")


@router.get("/tax-obligations")
async def get_tax_obligations(
    account_id: str = Depends(get_current_account),
    status: str = "all",
    db: Session = Depends(get_db),
):
    """Get tax obligations for the current account."""
    try:
        query = (
            select(TaxObligationRow)
            .where(TaxObligationRow.account_id == account_id)
            .order_by(TaxObligationRow.deadline.asc())
        )
        if status != "all":
            query = query.where(TaxObligationRow.status == status)

        rows = db.scalars(query).all()
        obligations = [_tax_obligation_to_dict(r) for r in rows]
        return {"obligations": obligations, "count": len(obligations)}
    except Exception as e:
        logger.error(f"Error fetching tax obligations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tax obligations")


@router.patch("/tax-obligations/{obligation_id}")
async def update_tax_obligation_status(
    obligation_id: str,
    new_status: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Update the status of a tax obligation (e.g., mark as completed)."""
    valid_statuses = ["pending", "reminded", "completed", "overdue"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    try:
        row = db.scalars(
            select(TaxObligationRow)
            .where(TaxObligationRow.id == obligation_id)
            .where(TaxObligationRow.account_id == account_id)
            .limit(1)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Obligation not found")
        row.status = new_status
        db.commit()
        db.refresh(row)
        return _tax_obligation_to_dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating obligation: {e}")
        raise HTTPException(status_code=500, detail="Failed to update obligation")


@router.get("/financial-insights")
async def get_financial_insights(
    account_id: str = Depends(get_current_account),
    acknowledged: bool = False,
    db: Session = Depends(get_db),
):
    """Get financial insights generated by agents."""
    try:
        rows = db.scalars(
            select(FinancialInsightRow)
            .where(FinancialInsightRow.account_id == account_id)
            .where(FinancialInsightRow.acknowledged == acknowledged)
            .order_by(FinancialInsightRow.created_at.desc())
            .limit(50)
        ).all()
        insights = [_financial_insight_to_dict(r) for r in rows]
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch insights")


@router.patch("/financial-insights/{insight_id}/acknowledge")
async def acknowledge_insight(
    insight_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Acknowledge a financial insight."""
    try:
        row = db.scalars(
            select(FinancialInsightRow)
            .where(FinancialInsightRow.id == insight_id)
            .where(FinancialInsightRow.account_id == account_id)
            .limit(1)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Insight not found")
        row.acknowledged = True
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging insight: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge insight")
