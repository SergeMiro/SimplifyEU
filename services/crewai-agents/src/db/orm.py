"""
SQLAlchemy 2.0 ORM models for the crewai-agents service.

These mirror db/migrations/0001_app_schema.sql exactly for the tables this
service reads/writes. Column types, nullability, defaults and FKs follow the SQL
source of truth. Server-side defaults (gen_random_uuid(), now(), and the literal
column defaults) are declared with `server_default` so the database fills them
in, matching the existing behavior.

Two groups of tables are modeled:

  * The crewai-agents-owned tables (business_profiles, agent_settings,
    tax_obligations, financial_insights, document_links, agent_execution_logs,
    agent_notifications). In the schema their `account_id` is a free-form TEXT
    tenant key (NOT an FK to accounts), so it is mapped as `Text`.

  * Cross-service read tables the agent tools query (analyses, analysis_items,
    invoices, duplicate_pairs). These are owned by the other services; they are
    declared here read-only so the tools can SELECT from them. `analyses` /
    `analysis_items` use UUID account/analysis ids; `duplicate_pairs` uses a
    VARCHAR account_id; `invoices` is the core Stripe billing table.

The schema uses bare TEXT for most string columns (some backed by CHECK
constraints, e.g. status / agent_type); those map to SQLAlchemy `Text`.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# =============================================================================
# CREWAI AGENTS OWNED TABLES (account_id is a free-form TEXT tenant key)
# =============================================================================


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    business_type: Mapped[str] = mapped_column(Text, nullable=False)
    tax_regime: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'micro'")
    )
    declaration_frequency: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'monthly'")
    )
    tva_applicable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    siret: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class AgentSetting(Base):
    __tablename__ = "agent_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'disabled'")
    )
    notification_channels: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[\"in_app\"]'::jsonb")
    )
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class TaxObligation(Base):
    __tablename__ = "tax_obligations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    obligation_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pending'")
    )
    draft_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    service_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class FinancialInsight(Base):
    __tablename__ = "financial_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    insight_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'info'")
    )
    data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class DocumentLink(Base):
    __tablename__ = "document_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(Text, nullable=False)
    flow_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'running'")
    )
    input_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    output_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentNotification(Base):
    __tablename__ = "agent_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'info'")
    )
    agent_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


# =============================================================================
# CROSS-SERVICE READ TABLES (owned by the other services; queried by tools)
# =============================================================================


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'csv'")
    )
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_transactions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subscriptions_found: Mapped[int] = mapped_column(
        Integer, nullable=True, server_default=text("0")
    )
    potential_savings_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=True, server_default=text("0")
    )
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class AnalysisItem(Base):
    __tablename__ = "analysis_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    merchant_descriptor: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_avg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    amount_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(
        Text, nullable=True, server_default=text("'EUR'")
    )
    frequency: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False)
    first_seen: Mapped[date] = mapped_column(Date, nullable=False)
    last_seen: Mapped[date] = mapped_column(Date, nullable=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    is_subscription: Mapped[bool] = mapped_column(
        Boolean, nullable=True, server_default=text("false")
    )
    tags: Mapped[list] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'")
    )
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )


class Invoice(Base):
    """Core Stripe billing invoices (accounts FK). NOTE: the document/calendar
    agent tools historically SELECT detector-only columns (vendor_name,
    total_amount, invoice_date, filename) from this table — that is a
    pre-existing mismatch (those columns live on `detector_invoices`), preserved
    here as-is; this model reflects the real `invoices` table."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    stripe_invoice_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric, nullable=False, server_default=text("0")
    )
    currency: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'eur'")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'draft'")
    )
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DuplicatePair(Base):
    __tablename__ = "duplicate_pairs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detector_invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detector_invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    similarity_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    match_details: Mapped[dict] = mapped_column(
        JSONB, nullable=True, server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=True, server_default=text("'pending'")
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
