"""
Database tools for CrewAI agents.
Provide agents with read access to transactions, invoices, analyses, and business data.
"""

import json
import logging
from datetime import datetime, timedelta
from crewai.tools import tool
from ..db.client import supabase

logger = logging.getLogger(__name__)


@tool("Get recent transactions")
def get_recent_transactions(account_id: str, days: int = 30) -> str:
    """
    Fetch recent bank transactions for an account from the analyses/analysis_items tables.
    Returns transactions from the last N days as a JSON string.
    """
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Get the latest completed analysis for this account
        analyses_res = (
            supabase.table("analyses")
            .select("id")
            .eq("account_id", account_id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not analyses_res.data:
            return json.dumps({"transactions": [], "message": "No completed analyses found"})

        analysis_id = analyses_res.data[0]["id"]

        # Fetch analysis items (detected subscriptions/transactions)
        items_res = (
            supabase.table("analysis_items")
            .select("*")
            .eq("analysis_id", analysis_id)
            .gte("created_at", cutoff)
            .execute()
        )

        return json.dumps({
            "transactions": items_res.data or [],
            "analysis_id": analysis_id,
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
        query = (
            supabase.table("invoices")
            .select("*")
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .limit(100)
        )

        if status_filter != "all":
            query = query.eq("status", status_filter)

        res = query.execute()
        return json.dumps({"invoices": res.data or [], "count": len(res.data or [])})
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
        res = (
            supabase.table("duplicate_pairs")
            .select("*")
            .eq("account_id", account_id)
            .eq("status", "pending")
            .order("similarity_score", desc=True)
            .execute()
        )
        return json.dumps({"duplicates": res.data or [], "count": len(res.data or [])})
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
        analysis_res = (
            supabase.table("analyses")
            .select("*")
            .eq("account_id", account_id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not analysis_res.data:
            return json.dumps({"message": "No subscription analysis found"})

        analysis = analysis_res.data[0]

        items_res = (
            supabase.table("analysis_items")
            .select("*")
            .eq("analysis_id", analysis["id"])
            .eq("is_subscription", True)
            .order("amount_avg", desc=True)
            .execute()
        )

        return json.dumps({
            "analysis": analysis,
            "subscriptions": items_res.data or [],
            "total_subscriptions": len(items_res.data or []),
            "potential_savings_eur": analysis.get("potential_savings_eur", 0),
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
        res = (
            supabase.table("financial_insights")
            .select("*")
            .eq("account_id", account_id)
            .eq("acknowledged", False)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return json.dumps({"insights": res.data or [], "count": len(res.data or [])})
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
        res = (
            supabase.table("financial_insights")
            .insert({
                "account_id": account_id,
                "insight_type": insight_type,
                "title": title,
                "description": description,
                "severity": severity,
                "data": parsed_data,
                "acknowledged": False,
            })
            .execute()
        )
        return json.dumps({"success": True, "insight_id": res.data[0]["id"] if res.data else None})
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
        query = (
            supabase.table("tax_obligations")
            .select("*")
            .eq("account_id", account_id)
            .order("deadline", desc=False)
        )

        if status_filter != "all":
            query = query.eq("status", status_filter)

        res = query.execute()
        return json.dumps({"obligations": res.data or [], "count": len(res.data or [])})
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
        insert_data = {
            "account_id": account_id,
            "obligation_type": obligation_type,
            "title": title,
            "description": description,
            "deadline": deadline,
            "status": "pending",
            "draft_data": parsed_draft,
        }
        if service_url:
            insert_data["service_url"] = service_url

        res = supabase.table("tax_obligations").insert(insert_data).execute()
        return json.dumps({"success": True, "obligation_id": res.data[0]["id"] if res.data else None})
    except Exception as e:
        logger.error(f"Error saving tax obligation: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Get business profile")
def get_business_profile(account_id: str) -> str:
    """
    Fetch the business profile for an account (type, tax regime, etc.).
    """
    try:
        res = (
            supabase.table("business_profiles")
            .select("*")
            .eq("account_id", account_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return json.dumps({"profile": res.data[0]})
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
        insert_data = {
            "account_id": account_id,
            "agent_type": agent_type,
            "flow_name": flow_name,
            "trigger": trigger,
            "status": status,
            "output_data": parsed_output,
        }
        if error_message:
            insert_data["error_message"] = error_message

        res = supabase.table("agent_execution_logs").insert(insert_data).execute()
        return json.dumps({"success": True, "log_id": res.data[0]["id"] if res.data else None})
    except Exception as e:
        logger.error(f"Error logging execution: {e}")
        return json.dumps({"error": str(e), "success": False})
