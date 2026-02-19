"""
API endpoints for managing agent settings (enable/disable, configure).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from ...auth.api_key import get_current_account
from ...db.client import supabase
from ...db.models import (
    AgentType,
    AgentSetting,
    AgentSettingUpdate,
    AgentToggleRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/agents")
async def list_agent_settings(account_id: str = Depends(get_current_account)):
    """List all agent settings for the current account."""
    try:
        res = (
            supabase.table("agent_settings")
            .select("*")
            .eq("account_id", account_id)
            .execute()
        )

        settings = res.data or []

        # If no settings exist yet, create defaults for all agent types
        if not settings:
            defaults = []
            for agent_type in AgentType:
                default = {
                    "account_id": account_id,
                    "agent_type": agent_type.value,
                    "status": "disabled",
                    "notification_channels": ["in_app"],
                    "config": {},
                }
                defaults.append(default)

            res = supabase.table("agent_settings").insert(defaults).execute()
            settings = res.data or []

        return {"agents": settings, "count": len(settings)}
    except Exception as e:
        logger.error(f"Error listing agent settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch agent settings")


@router.get("/agents/{agent_type}")
async def get_agent_setting(
    agent_type: AgentType,
    account_id: str = Depends(get_current_account),
):
    """Get settings for a specific agent type."""
    try:
        res = (
            supabase.table("agent_settings")
            .select("*")
            .eq("account_id", account_id)
            .eq("agent_type", agent_type.value)
            .limit(1)
            .execute()
        )

        if not res.data:
            # Create default setting
            default = {
                "account_id": account_id,
                "agent_type": agent_type.value,
                "status": "disabled",
                "notification_channels": ["in_app"],
                "config": {},
            }
            res = supabase.table("agent_settings").insert(default).execute()

        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error getting agent setting: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch agent setting")


@router.patch("/agents/{agent_type}")
async def update_agent_setting(
    agent_type: AgentType,
    update: AgentSettingUpdate,
    account_id: str = Depends(get_current_account),
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

        res = (
            supabase.table("agent_settings")
            .update(update_data)
            .eq("account_id", account_id)
            .eq("agent_type", agent_type.value)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Agent setting not found")

        return res.data[0]
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
):
    """Quick toggle to enable/disable an agent."""
    try:
        res = (
            supabase.table("agent_settings")
            .update({"status": toggle.status.value})
            .eq("account_id", account_id)
            .eq("agent_type", agent_type.value)
            .execute()
        )

        if not res.data:
            # Create if doesn't exist
            res = (
                supabase.table("agent_settings")
                .insert({
                    "account_id": account_id,
                    "agent_type": agent_type.value,
                    "status": toggle.status.value,
                    "notification_channels": ["in_app"],
                    "config": {},
                })
                .execute()
            )

        return {"agent_type": agent_type.value, "status": toggle.status.value}
    except Exception as e:
        logger.error(f"Error toggling agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle agent")


@router.get("/agents/logs/recent")
async def get_recent_execution_logs(
    account_id: str = Depends(get_current_account),
    limit: int = 20,
):
    """Get recent agent execution logs for transparency."""
    try:
        res = (
            supabase.table("agent_execution_logs")
            .select("*")
            .eq("account_id", account_id)
            .order("started_at", desc=True)
            .limit(min(limit, 100))
            .execute()
        )
        return {"logs": res.data or [], "count": len(res.data or [])}
    except Exception as e:
        logger.error(f"Error fetching execution logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch logs")


@router.get("/notifications")
async def get_notifications(
    account_id: str = Depends(get_current_account),
    unread_only: bool = True,
    limit: int = 50,
):
    """Get agent notifications for the user dashboard."""
    try:
        query = (
            supabase.table("agent_notifications")
            .select("*")
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .limit(min(limit, 100))
        )

        if unread_only:
            query = query.eq("read", False)

        res = query.execute()
        return {"notifications": res.data or [], "count": len(res.data or [])}
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    account_id: str = Depends(get_current_account),
):
    """Mark a notification as read."""
    try:
        res = (
            supabase.table("agent_notifications")
            .update({"read": True})
            .eq("id", notification_id)
            .eq("account_id", account_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")
