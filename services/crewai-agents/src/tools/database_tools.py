"""
Database tools for CrewAI agents.
Provide agents with read access to transactions, invoices, analyses, and business data.
"""

import json
import logging
from datetime import datetime, timedelta
from crewai.tools import tool
from sqlalchemy import select
from ..db.session import SessionLocal
from ..db.orm import (
    Analysis as AnalysisRow,
    AnalysisItem as AnalysisItemRow,
    Invoice as InvoiceRow,
    DuplicatePair as DuplicatePairRow,
    FinancialInsight as FinancialInsightRow,
    TaxObligation as TaxObligationRow,
    BusinessProfile as BusinessProfileRow,
    AgentExecutionLog as AgentExecutionLogRow,
)

logger = logging.getLogger(__name__)


def _analysis_to_dict(a: AnalysisRow) -> dict:
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


def _analysis_item_to_dict(i: AnalysisItemRow) -> dict:
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
        "tags": i.tags,
        "recommendation": i.recommendation,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _invoice_to_dict(inv: InvoiceRow) -> dict:
    return {
        "id": str(inv.id),
        "account_id": str(inv.account_id),
        "stripe_invoice_id": inv.stripe_invoice_id,
        "amount": float(inv.amount) if inv.amount is not None else None,
        "currency": inv.currency,
        "status": inv.status,
        "pdf_url": inv.pdf_url,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


def _duplicate_pair_to_dict(d: DuplicatePairRow) -> dict:
    return {
        "id": str(d.id),
        "account_id": d.account_id,
        "invoice_a_id": str(d.invoice_a_id),
        "invoice_b_id": str(d.invoice_b_id),
        "similarity_score": float(d.similarity_score) if d.similarity_score is not None else None,
        "match_details": d.match_details,
        "status": d.status,
        "reviewed_by": d.reviewed_by,
        "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
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


@tool("Get recent transactions")
def get_recent_transactions(account_id: str, days: int = 30) -> str:
    """
    Fetch recent bank transactions for an account from the analyses/analysis_items tables.
    Returns transactions from the last N days as a JSON string.
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)

        with SessionLocal() as db:
            # Get the latest completed analysis for this account
            analysis = db.scalars(
                select(AnalysisRow)
                .where(AnalysisRow.account_id == account_id)
                .where(AnalysisRow.status == "completed")
                .order_by(AnalysisRow.created_at.desc())
                .limit(1)
            ).first()

            if analysis is None:
                return json.dumps({"transactions": [], "message": "No completed analyses found"})

            analysis_id = analysis.id

            # Fetch analysis items (detected subscriptions/transactions)
            items = db.scalars(
                select(AnalysisItemRow)
                .where(AnalysisItemRow.analysis_id == analysis_id)
                .where(AnalysisItemRow.created_at >= cutoff)
            ).all()

            return json.dumps({
                "transactions": [_analysis_item_to_dict(i) for i in items],
                "analysis_id": str(analysis_id),
                "period_days": days,
            })
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return json.dumps({"error": str(e), "transactions": []})


@tool("Get invoices for account")
def get_invoices(account_id: str, status_filter: str = "all") -> str:
    """
    Fetch invoices for an account. Can filter by status (all, pending, confirmed, dismissed).
    Returns invoices as a JSON string.
    """
    try:
        with SessionLocal() as db:
            query = (
                select(InvoiceRow)
                .where(InvoiceRow.account_id == account_id)
                .order_by(InvoiceRow.created_at.desc())
                .limit(100)
            )

            if status_filter != "all":
                query = query.where(InvoiceRow.status == status_filter)

            rows = db.scalars(query).all()
            invoices = [_invoice_to_dict(r) for r in rows]
            return json.dumps({"invoices": invoices, "count": len(invoices)})
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        return json.dumps({"error": str(e), "invoices": []})


@tool("Get duplicate pairs")
def get_duplicate_pairs(account_id: str) -> str:
    """
    Fetch detected duplicate invoice pairs for an account.
    Returns pending duplicates that need review.
    """
    try:
        with SessionLocal() as db:
            rows = db.scalars(
                select(DuplicatePairRow)
                .where(DuplicatePairRow.account_id == account_id)
                .where(DuplicatePairRow.status == "pending")
                .order_by(DuplicatePairRow.similarity_score.desc())
            ).all()
            duplicates = [_duplicate_pair_to_dict(r) for r in rows]
            return json.dumps({"duplicates": duplicates, "count": len(duplicates)})
    except Exception as e:
        logger.error(f"Error fetching duplicates: {e}")
        return json.dumps({"error": str(e), "duplicates": []})


@tool("Get subscription analysis")
def get_subscription_analysis(account_id: str) -> str:
    """
    Fetch the latest subscription analysis results for an account.
    Includes detected subscriptions, amounts, and savings potential.
    """
    try:
        with SessionLocal() as db:
            analysis = db.scalars(
                select(AnalysisRow)
                .where(AnalysisRow.account_id == account_id)
                .where(AnalysisRow.status == "completed")
                .order_by(AnalysisRow.created_at.desc())
                .limit(1)
            ).first()

            if analysis is None:
                return json.dumps({"message": "No subscription analysis found"})

            items = db.scalars(
                select(AnalysisItemRow)
                .where(AnalysisItemRow.analysis_id == analysis.id)
                .where(AnalysisItemRow.is_subscription == True)  # noqa: E712
                .order_by(AnalysisItemRow.amount_avg.desc())
            ).all()

            return json.dumps({
                "analysis": _analysis_to_dict(analysis),
                "subscriptions": [_analysis_item_to_dict(i) for i in items],
                "total_subscriptions": len(items),
                "potential_savings_eur": float(analysis.potential_savings_eur) if analysis.potential_savings_eur is not None else 0,
            })
    except Exception as e:
        logger.error(f"Error fetching subscription analysis: {e}")
        return json.dumps({"error": str(e)})


@tool("Get financial insights")
def get_financial_insights(account_id: str) -> str:
    """
    Fetch stored financial insights for an account (anomalies, trends, recommendations).
    """
    try:
        with SessionLocal() as db:
            rows = db.scalars(
                select(FinancialInsightRow)
                .where(FinancialInsightRow.account_id == account_id)
                .where(FinancialInsightRow.acknowledged == False)  # noqa: E712
                .order_by(FinancialInsightRow.created_at.desc())
                .limit(20)
            ).all()
            insights = [_financial_insight_to_dict(r) for r in rows]
            return json.dumps({"insights": insights, "count": len(insights)})
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        return json.dumps({"error": str(e), "insights": []})


@tool("Save financial insight")
def save_financial_insight(
    account_id: str,
    insight_type: str,
    title: str,
    description: str,
    severity: str = "info",
    data: str = "{}",
) -> str:
    """
    Save a new financial insight to the database.
    insight_type: anomaly, trend, subscription, recommendation
    severity: info, warning, critical
    data: JSON string with additional data
    """
    try:
        parsed_data = json.loads(data) if isinstance(data, str) else data
        with SessionLocal() as db:
            row = FinancialInsightRow(
                account_id=account_id,
                insight_type=insight_type,
                title=title,
                description=description,
                severity=severity,
                data=parsed_data,
                acknowledged=False,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return json.dumps({"success": True, "insight_id": str(row.id)})
    except Exception as e:
        logger.error(f"Error saving insight: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Get tax obligations")
def get_tax_obligations(account_id: str, status_filter: str = "pending") -> str:
    """
    Fetch tax obligations/deadlines for an account.
    status_filter: pending, reminded, completed, overdue, all
    """
    try:
        with SessionLocal() as db:
            query = (
                select(TaxObligationRow)
                .where(TaxObligationRow.account_id == account_id)
                .order_by(TaxObligationRow.deadline.asc())
            )

            if status_filter != "all":
                query = query.where(TaxObligationRow.status == status_filter)

            rows = db.scalars(query).all()
            obligations = [_tax_obligation_to_dict(r) for r in rows]
            return json.dumps({"obligations": obligations, "count": len(obligations)})
    except Exception as e:
        logger.error(f"Error fetching tax obligations: {e}")
        return json.dumps({"error": str(e), "obligations": []})


@tool("Save tax obligation")
def save_tax_obligation(
    account_id: str,
    obligation_type: str,
    title: str,
    deadline: str,
    description: str = "",
    service_url: str = "",
    draft_data: str = "{}",
) -> str:
    """
    Save a tax obligation/deadline to the database.
    deadline: ISO format datetime string (e.g., '2025-04-30T23:59:00')
    """
    try:
        parsed_draft = json.loads(draft_data) if isinstance(draft_data, str) else draft_data
        with SessionLocal() as db:
            row = TaxObligationRow(
                account_id=account_id,
                obligation_type=obligation_type,
                title=title,
                description=description,
                deadline=deadline,
                status="pending",
                draft_data=parsed_draft,
            )
            if service_url:
                row.service_url = service_url

            db.add(row)
            db.commit()
            db.refresh(row)
            return json.dumps({"success": True, "obligation_id": str(row.id)})
    except Exception as e:
        logger.error(f"Error saving tax obligation: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Get business profile")
def get_business_profile(account_id: str) -> str:
    """
    Fetch the business profile for an account (type, tax regime, etc.).
    """
    try:
        with SessionLocal() as db:
            row = db.scalars(
                select(BusinessProfileRow)
                .where(BusinessProfileRow.account_id == account_id)
                .limit(1)
            ).first()
            if row is not None:
                return json.dumps({"profile": _business_profile_to_dict(row)})
            return json.dumps({"profile": None, "message": "No business profile found"})
    except Exception as e:
        logger.error(f"Error fetching business profile: {e}")
        return json.dumps({"error": str(e), "profile": None})


@tool("Log agent execution")
def log_agent_execution(
    account_id: str,
    agent_type: str,
    flow_name: str,
    trigger: str,
    status: str,
    output_data: str = "{}",
    error_message: str = "",
) -> str:
    """
    Log an agent execution event to the database for audit/transparency.
    """
    try:
        parsed_output = json.loads(output_data) if isinstance(output_data, str) else output_data
        with SessionLocal() as db:
            row = AgentExecutionLogRow(
                account_id=account_id,
                agent_type=agent_type,
                flow_name=flow_name,
                trigger=trigger,
                status=status,
                output_data=parsed_output,
            )
            if error_message:
                row.error_message = error_message

            db.add(row)
            db.commit()
            db.refresh(row)
            return json.dumps({"success": True, "log_id": str(row.id)})
    except Exception as e:
        logger.error(f"Error logging execution: {e}")
        return json.dumps({"error": str(e), "success": False})
