"""
API endpoints for triggering and managing agent flows.
"""

import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...auth.api_key import get_current_account
from ...db.session import SessionLocal, get_db
from ...db.orm import (
    AgentSetting as AgentSettingRow,
    AgentExecutionLog as AgentExecutionLogRow,
)
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


def _execution_log_to_dict(log: AgentExecutionLogRow) -> dict:
    return {
        "id": str(log.id),
        "account_id": log.account_id,
        "agent_type": log.agent_type,
        "flow_name": log.flow_name,
        "trigger": log.trigger,
        "status": log.status,
        "input_data": log.input_data,
        "output_data": log.output_data,
        "error_message": log.error_message,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    }


def _is_agent_enabled(db: Session, account_id: str, agent_type: str) -> bool:
    """Check if the corresponding agent is enabled for this account."""
    try:
        row = db.scalars(
            select(AgentSettingRow)
            .where(AgentSettingRow.account_id == account_id)
            .where(AgentSettingRow.agent_type == agent_type)
            .limit(1)
        ).first()
        if row is not None:
            return row.status == "enabled"
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
        with SessionLocal() as db:
            db.add(
                AgentExecutionLogRow(
                    id=uuid.UUID(execution_id),
                    account_id=account_id,
                    agent_type=flow_info["agent_type"],
                    flow_name=flow_name,
                    trigger=trigger,
                    status="running",
                    input_data=trigger_data,
                )
            )
            db.commit()
    except Exception as e:
        logger.error(f"Failed to create execution log: {e}")

    try:
        flow = flow_class()
        flow.state.account_id = account_id
        flow.state.trigger = trigger
        result = flow.kickoff()

        # Update execution log on success
        with SessionLocal() as db:
            log = db.get(AgentExecutionLogRow, uuid.UUID(execution_id))
            if log is not None:
                log.status = "completed"
                log.output_data = {"result": str(result)}
                log.completed_at = datetime.now(timezone.utc)
                db.commit()

        logger.info(f"Flow '{flow_name}' completed for account {account_id}")
    except Exception as e:
        logger.error(f"Flow '{flow_name}' failed: {e}")
        try:
            with SessionLocal() as db:
                log = db.get(AgentExecutionLogRow, uuid.UUID(execution_id))
                if log is not None:
                    log.status = "failed"
                    log.error_message = str(e)
                    log.completed_at = datetime.now(timezone.utc)
                    db.commit()
        except Exception:
            pass


@router.get("/flows")
async def list_available_flows(
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """List all available flows and their current status."""
    flows = []
    for name, info in FLOW_REGISTRY.items():
        enabled = _is_agent_enabled(db, account_id, info["agent_type"])
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
    db: Session = Depends(get_db),
):
    """Trigger a specific flow for the current account."""
    if flow_name not in FLOW_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Flow '{flow_name}' not found. Available: {list(FLOW_REGISTRY.keys())}",
        )

    flow_info = FLOW_REGISTRY[flow_name]

    # Check if agent is enabled
    if not _is_agent_enabled(db, account_id, flow_info["agent_type"]):
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
    db: Session = Depends(get_db),
):
    """Get recent flow execution history."""
    try:
        query = (
            select(AgentExecutionLogRow)
            .where(AgentExecutionLogRow.account_id == account_id)
            .order_by(AgentExecutionLogRow.started_at.desc())
            .limit(min(limit, 100))
        )

        if flow_name:
            query = query.where(AgentExecutionLogRow.flow_name == flow_name)

        rows = db.scalars(query).all()
        executions = [_execution_log_to_dict(r) for r in rows]
        return {"executions": executions, "count": len(executions)}
    except Exception as e:
        logger.error(f"Error fetching executions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch executions")


@router.get("/flows/executions/{execution_id}")
async def get_execution_detail(
    execution_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Get details of a specific flow execution."""
    try:
        row = db.scalars(
            select(AgentExecutionLogRow)
            .where(AgentExecutionLogRow.id == execution_id)
            .where(AgentExecutionLogRow.account_id == account_id)
            .limit(1)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Execution not found")
        return _execution_log_to_dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch execution")
