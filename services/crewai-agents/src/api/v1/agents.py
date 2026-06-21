"""
API endpoints for managing agent settings (enable/disable, configure).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...auth.api_key import get_current_account
from ...db.session import get_db
from ...db.orm import (
    AgentSetting as AgentSettingRow,
    AgentExecutionLog as AgentExecutionLogRow,
    AgentNotification as AgentNotificationRow,
)
from ...db.models import (
    AgentType,
    AgentSetting,
    AgentSettingUpdate,
    AgentToggleRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _agent_setting_to_dict(s: AgentSettingRow) -> dict:
    return {
        "id": str(s.id),
        "account_id": s.account_id,
        "agent_type": s.agent_type,
        "status": s.status,
        "notification_channels": s.notification_channels,
        "config": s.config,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
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


def _notification_to_dict(n: AgentNotificationRow) -> dict:
    return {
        "id": str(n.id),
        "account_id": n.account_id,
        "title": n.title,
        "message": n.message,
        "notification_type": n.notification_type,
        "agent_type": n.agent_type,
        "action_url": n.action_url,
        "read": n.read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/agents")
async def list_agent_settings(
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """List all agent settings for the current account."""
    try:
        rows = db.scalars(
            select(AgentSettingRow).where(AgentSettingRow.account_id == account_id)
        ).all()

        # If no settings exist yet, create defaults for all agent types
        if not rows:
            for agent_type in AgentType:
                db.add(
                    AgentSettingRow(
                        account_id=account_id,
                        agent_type=agent_type.value,
                        status="disabled",
                        notification_channels=["in_app"],
                        config={},
                    )
                )
            db.commit()
            rows = db.scalars(
                select(AgentSettingRow).where(AgentSettingRow.account_id == account_id)
            ).all()

        settings = [_agent_setting_to_dict(r) for r in rows]
        return {"agents": settings, "count": len(settings)}
    except Exception as e:
        logger.error(f"Error listing agent settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch agent settings")


@router.get("/agents/{agent_type}")
async def get_agent_setting(
    agent_type: AgentType,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Get settings for a specific agent type."""
    try:
        row = db.scalars(
            select(AgentSettingRow)
            .where(AgentSettingRow.account_id == account_id)
            .where(AgentSettingRow.agent_type == agent_type.value)
            .limit(1)
        ).first()

        if row is None:
            # Create default setting
            row = AgentSettingRow(
                account_id=account_id,
                agent_type=agent_type.value,
                status="disabled",
                notification_channels=["in_app"],
                config={},
            )
            db.add(row)
            db.commit()
            db.refresh(row)

        return _agent_setting_to_dict(row)
    except Exception as e:
        logger.error(f"Error getting agent setting: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch agent setting")


@router.patch("/agents/{agent_type}")
async def update_agent_setting(
    agent_type: AgentType,
    update: AgentSettingUpdate,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Update settings for a specific agent type."""
    try:
        update_data = {}
        if update.status is not None:
            update_data["status"] = update.status.value
        if update.notification_channels is not None:
            update_data["notification_channels"] = [
                ch.value for ch in update.notification_channels
            ]
        if update.config is not None:
            update_data["config"] = update.config

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        row = db.scalars(
            select(AgentSettingRow)
            .where(AgentSettingRow.account_id == account_id)
            .where(AgentSettingRow.agent_type == agent_type.value)
            .limit(1)
        ).first()

        if row is None:
            raise HTTPException(status_code=404, detail="Agent setting not found")

        for field, value in update_data.items():
            setattr(row, field, value)
        db.commit()
        db.refresh(row)

        return _agent_setting_to_dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent setting: {e}")
        raise HTTPException(status_code=500, detail="Failed to update agent setting")


@router.post("/agents/{agent_type}/toggle")
async def toggle_agent(
    agent_type: AgentType,
    toggle: AgentToggleRequest,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Quick toggle to enable/disable an agent."""
    try:
        row = db.scalars(
            select(AgentSettingRow)
            .where(AgentSettingRow.account_id == account_id)
            .where(AgentSettingRow.agent_type == agent_type.value)
            .limit(1)
        ).first()

        if row is None:
            # Create if doesn't exist
            row = AgentSettingRow(
                account_id=account_id,
                agent_type=agent_type.value,
                status=toggle.status.value,
                notification_channels=["in_app"],
                config={},
            )
            db.add(row)
        else:
            row.status = toggle.status.value
        db.commit()

        return {"agent_type": agent_type.value, "status": toggle.status.value}
    except Exception as e:
        logger.error(f"Error toggling agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle agent")


@router.get("/agents/logs/recent")
async def get_recent_execution_logs(
    account_id: str = Depends(get_current_account),
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Get recent agent execution logs for transparency."""
    try:
        rows = db.scalars(
            select(AgentExecutionLogRow)
            .where(AgentExecutionLogRow.account_id == account_id)
            .order_by(AgentExecutionLogRow.started_at.desc())
            .limit(min(limit, 100))
        ).all()
        logs = [_execution_log_to_dict(r) for r in rows]
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error fetching execution logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch logs")


@router.get("/notifications")
async def get_notifications(
    account_id: str = Depends(get_current_account),
    unread_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get agent notifications for the user dashboard."""
    try:
        query = (
            select(AgentNotificationRow)
            .where(AgentNotificationRow.account_id == account_id)
            .order_by(AgentNotificationRow.created_at.desc())
            .limit(min(limit, 100))
        )

        if unread_only:
            query = query.where(AgentNotificationRow.read == False)  # noqa: E712

        rows = db.scalars(query).all()
        notifications = [_notification_to_dict(r) for r in rows]
        return {"notifications": notifications, "count": len(notifications)}
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    account_id: str = Depends(get_current_account),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    try:
        row = db.scalars(
            select(AgentNotificationRow)
            .where(AgentNotificationRow.id == notification_id)
            .where(AgentNotificationRow.account_id == account_id)
            .limit(1)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        row.read = True
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")
