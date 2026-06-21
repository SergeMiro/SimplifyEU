"""
SQLAlchemy 2.0 ORM models for the invoice-detector tables.

These mirror db/migrations/0001_app_schema.sql exactly for the two tables this
service owns: detector_invoices and duplicate_pairs. Column types, nullability,
defaults and FKs follow the SQL source of truth. Server-side defaults
(gen_random_uuid(), now(), and the literal column defaults) are declared with
`server_default` so the database fills them in, matching the existing behavior.

IMPORTANT: the detector's table was renamed `invoices` -> `detector_invoices`
in Phase 2 (the bare `invoices` table is now the separate BILLING table). All
invoice access in this service goes through DetectorInvoice / detector_invoices.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


class DetectorInvoice(Base):
    __tablename__ = "detector_invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    invoice_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(
        String(10), nullable=True, server_default=text("'EUR'")
    )
    line_items: Mapped[list] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'")
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_used: Mapped[bool] = mapped_column(
        Boolean, nullable=True, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=True, server_default=text("'pending'")
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
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
