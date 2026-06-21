"""
SQLAlchemy 2.0 ORM models for the subscription-analyzer tables.

These mirror db/migrations/0001_app_schema.sql exactly for the two tables this
service owns: analyses and analysis_items. Column types, nullability, defaults
and FKs follow the SQL source of truth. Server-side defaults (gen_random_uuid(),
now(), and the literal column defaults) are declared with `server_default` so the
database fills them in, matching the existing behavior.

The schema uses bare TEXT for the string columns (some backed by CHECK
constraints, e.g. status / frequency); those map to SQLAlchemy `Text`. The FKs on
analyses.account_id / analyses.user_id point at accounts(id) / users(id).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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
