from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    FINANCIAL = "financial_assistant"
    TAX = "tax_assistant"
    DOCUMENT = "document_manager"
    CLIENT = "client_assistant"
    OPERATIONS = "operations_coordinator"


class AgentStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class BusinessType(str, Enum):
    MICRO_ENTREPRENEUR = "micro_entrepreneur"
    SARL = "sarl"
    SAS = "sas"
    SASU = "sasu"
    EI = "ei"
    EURL = "eurl"
    OTHER = "other"


class TaxRegime(str, Enum):
    MICRO = "micro"
    REEL_SIMPLIFIE = "reel_simplifie"
    REEL_NORMAL = "reel_normal"


class DeclarationFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class NotificationChannel(str, Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    IN_APP = "in_app"


# --- Agent Settings ---

class AgentSetting(BaseModel):
    id: str | None = None
    account_id: str
    agent_type: AgentType
    status: AgentStatus = AgentStatus.DISABLED
    notification_channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.IN_APP]
    )
    config: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentSettingUpdate(BaseModel):
    status: AgentStatus | None = None
    notification_channels: list[NotificationChannel] | None = None
    config: dict | None = None


# --- Business Profile ---

class BusinessProfile(BaseModel):
    id: str | None = None
    account_id: str
    business_type: BusinessType
    tax_regime: TaxRegime = TaxRegime.MICRO
    declaration_frequency: DeclarationFrequency = DeclarationFrequency.MONTHLY
    tva_applicable: bool = False
    siret: str | None = None
    created_at: datetime | None = None


# --- Tax Calendar ---

class TaxObligation(BaseModel):
    id: str | None = None
    account_id: str
    obligation_type: str  # e.g., "declaration_ca", "tva", "cotisations"
    title: str
    description: str | None = None
    deadline: datetime
    status: str = "pending"  # pending, reminded, completed, overdue
    draft_data: dict | None = None
    service_url: str | None = None
    created_at: datetime | None = None


# --- Transaction Tags ---

class TransactionTag(BaseModel):
    id: str | None = None
    account_id: str
    transaction_id: str
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    notes: str | None = None


# --- Financial Insights ---

class FinancialInsight(BaseModel):
    id: str | None = None
    account_id: str
    insight_type: str  # anomaly, trend, subscription, recommendation
    title: str
    description: str
    severity: str = "info"  # info, warning, critical
    data: dict = Field(default_factory=dict)
    acknowledged: bool = False
    created_at: datetime | None = None


# --- Document Links ---

class DocumentLink(BaseModel):
    id: str | None = None
    account_id: str
    document_id: str
    transaction_id: str | None = None
    match_confidence: float | None = None
    verified: bool = False
    created_at: datetime | None = None


# --- Agent Execution Log ---

class AgentExecutionLog(BaseModel):
    id: str | None = None
    account_id: str
    agent_type: AgentType
    flow_name: str | None = None
    trigger: str | None = None
    status: str = "running"  # running, completed, failed
    input_data: dict = Field(default_factory=dict)
    output_data: dict = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# --- Weekly Report ---

class WeeklyReport(BaseModel):
    id: str | None = None
    account_id: str
    period_start: datetime
    period_end: datetime
    summary: str
    highlights: list[dict] = Field(default_factory=list)
    action_items: list[dict] = Field(default_factory=list)
    financial_snapshot: dict = Field(default_factory=dict)
    created_at: datetime | None = None


# --- API Request/Response models ---

class AgentToggleRequest(BaseModel):
    status: AgentStatus


class FlowTriggerRequest(BaseModel):
    flow_name: str
    trigger_data: dict = Field(default_factory=dict)


class FlowTriggerResponse(BaseModel):
    execution_id: str
    status: str
    message: str
