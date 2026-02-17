from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID


class Team(BaseModel):
    id: UUID
    slack_team_id: str
    name: str
    subscription_tier: Literal["free", "starter", "pro"] = "free"
    reminders_count: int = 0
    max_reminders: int = 50
    created_at: datetime
    updated_at: datetime


class Reminder(BaseModel):
    id: UUID
    team_id: UUID
    creator_user_id: str
    target_user_id: str
    task_text: str
    context: Optional[str] = None
    project: Optional[str] = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    remind_at: datetime
    status: Literal["pending", "sent", "completed", "cancelled", "failed", "snoozed"] = "pending"
    repeat: Optional[Literal["daily", "weekly", "biweekly", "monthly"]] = None
    parent_reminder_id: Optional[UUID] = None
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    snooze_count: int = 0
    retry_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ContextEvent(BaseModel):
    id: UUID
    team_id: UUID
    user_id: str
    event_type: Literal["reminder_created", "reminder_sent", "reminder_completed",
                         "reminder_cancelled", "reminder_snoozed"]
    event_data: dict = {}
    related_reminder_id: Optional[UUID] = None
    created_at: datetime


class ReminderCreate(BaseModel):
    target_user_id: str
    task_text: str = Field(..., min_length=1, max_length=2000)
    context: Optional[str] = Field(None, max_length=5000)
    project: Optional[str] = Field(None, max_length=200)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    remind_at: Optional[datetime] = None
    remind_at_text: Optional[str] = Field(None, max_length=200)
    repeat: Optional[Literal["daily", "weekly", "biweekly", "monthly"]] = None


class ReminderUpdate(BaseModel):
    task_text: Optional[str] = Field(None, min_length=1, max_length=2000)
    context: Optional[str] = Field(None, max_length=5000)
    project: Optional[str] = Field(None, max_length=200)
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = None
    remind_at: Optional[datetime] = None
    status: Optional[Literal["pending", "completed", "cancelled"]] = None


class TeamCreate(BaseModel):
    slack_team_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
