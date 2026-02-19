"""
API endpoints for triggering and managing agent flows.
"""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from ...auth.api_key import get_current_account
from ...db.client import supabase
from ...db.models import FlowTriggerRequest, FlowTriggerResponse
from ...flows import (
    FinancialFlow,
    TaxFlow,
    DocumentFlow,
    ClientFlow,
    OperationsFlow,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Map flow names to their classes and required agent types
FLOW_REGISTRY = {
    "financial": {
        "flow_class": FinancialFlow,
        "agent_type": "financial_assistant",
        "description": "Analyze bank transactions for anomalies and insights",
    },
    "tax": {
        "flow_class": TaxFlow,
        "agent_type": "tax_assistant",
        "description": "Check tax deadlines and prepare declarations",
    },
    "document": {
        "flow_class": DocumentFlow,
        "agent_type": "document_manager",
        "description": "Match documents to transactions",
    },
    "client": {
        "flow_class": ClientFlow,
        "agent_type": "client_assistant",
        "description": "Check overdue invoices and prepare reminders",
    },
    "operations": {
        "flow_class": OperationsFlow,
        "agent_type": "operations_coordinator",
        "description": "Generate weekly operational briefing",
    },
}


def _is_agent_enabled(account_id: str, agent_type: str) -> bool:
    """Check if the corresponding agent is enabled for this account."""
    try:
        res = (
            supabase.table("agent_settings")
            .select("status")
            .eq("account_id", account_id)
            .eq("agent_type", agent_type)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0].get("status") == "enabled"
        return False
    except Exception:
        return False


def _run_flow_in_background(
    flow_name: str,
    account_id: str,
    trigger: str,
    execution_id: str,
    trigger_data: dict,
):
    """Run a flow in the background."""
    flow_info = FLOW_REGISTRY[flow_name]
    flow_class = flow_info["flow_class"]

    # Create execution log
    try:
        supabase.table("agent_execution_logs").insert({
            "id": execution_id,
            "account_id": account_id,
            "agent_type": flow_info["agent_type"],
            "flow_name": flow_name,
            "trigger": trigger,
            "status": "running",
            "input_data": trigger_data,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to create execution log: {e}")

    try:
        flow = flow_class()
        flow.state.account_id = account_id
        flow.state.trigger = trigger
        result = flow.kickoff()

        # Update execution log on success
        supabase.table("agent_execution_logs").update({
            "status": "completed",
            "output_data": {"result": str(result)},
        }).eq("id", execution_id).execute()

        logger.info(f"Flow '{flow_name}' completed for account {account_id}")
    except Exception as e:
        logger.error(f"Flow '{flow_name}' failed: {e}")
        try:
            supabase.table("agent_execution_logs").update({
                "status": "failed",
                "error_message": str(e),
            }).eq("id", execution_id).execute()
        except Exception:
            pass


@router.get("/flows")
async def list_available_flows(account_id: str = Depends(get_current_account)):
    """List all available flows and their current status."""
    flows = []
    for name, info in FLOW_REGISTRY.items():
        enabled = _is_agent_enabled(account_id, info["agent_type"])
        flows.append({
            "name": name,
            "agent_type": info["agent_type"],
            "description": info["description"],
            "enabled": enabled,
        })
    return {"flows": flows}


@router.post("/flows/{flow_name}/trigger", response_model=FlowTriggerResponse)
async def trigger_flow(
    flow_name: str,
    background_tasks: BackgroundTasks,
    trigger_data: FlowTriggerRequest | None = None,
    account_id: str = Depends(get_current_account),
):
    """Trigger a specific flow for the current account."""
    if flow_name not in FLOW_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Flow '{flow_name}' not found. Available: {list(FLOW_REGISTRY.keys())}",
        )

    flow_info = FLOW_REGISTRY[flow_name]

    # Check if agent is enabled
    if not _is_agent_enabled(account_id, flow_info["agent_type"]):
        raise HTTPException(
            status_code=403,
            detail=f"Agent '{flow_info['agent_type']}' is not enabled. "
            f"Enable it in your agent settings first.",
        )

    execution_id = str(uuid.uuid4())
    data = trigger_data.trigger_data if trigger_data else {}

    background_tasks.add_task(
        _run_flow_in_background,
        flow_name=flow_name,
        account_id=account_id,
        trigger="manual",
        execution_id=execution_id,
        trigger_data=data,
    )

    return FlowTriggerResponse(
        execution_id=execution_id,
        status="started",
        message=f"Flow '{flow_name}' started in background. Check execution logs for status.",
    )


@router.get("/flows/executions")
async def get_flow_executions(
    account_id: str = Depends(get_current_account),
    flow_name: str | None = None,
    limit: int = 20,
):
    """Get recent flow execution history."""
    try:
        query = (
            supabase.table("agent_execution_logs")
            .select("*")
            .eq("account_id", account_id)
            .order("started_at", desc=True)
            .limit(min(limit, 100))
        )

        if flow_name:
            query = query.eq("flow_name", flow_name)

        res = query.execute()
        return {"executions": res.data or [], "count": len(res.data or [])}
    except Exception as e:
        logger.error(f"Error fetching executions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch executions")


@router.get("/flows/executions/{execution_id}")
async def get_execution_detail(
    execution_id: str,
    account_id: str = Depends(get_current_account),
):
    """Get details of a specific flow execution."""
    try:
        res = (
            supabase.table("agent_execution_logs")
            .select("*")
            .eq("id", execution_id)
            .eq("account_id", account_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Execution not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch execution")
