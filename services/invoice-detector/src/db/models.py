"""
Pydantic models for Invoice Duplicate Detector.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Invoice(BaseModel):
    """Stored invoice record."""
    id: str
    account_id: str
    filename: str
    file_hash: str
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "EUR"
    line_items: Optional[list] = None
    raw_text: Optional[str] = None
    ocr_used: bool = False
    status: str = "pending"  # pending | processed | error
    processing_error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DuplicatePair(BaseModel):
    """A pair of potentially duplicate invoices."""
    id: str
    account_id: str
    invoice_a_id: str
    invoice_b_id: str
    similarity_score: float
    match_details: Optional[dict] = None
    status: str = "pending"  # pending | confirmed | dismissed
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None


class InvoiceUploadResponse(BaseModel):
    """Response after uploading an invoice."""
    id: str
    filename: str
    status: str
    duplicates_found: int = 0


class DuplicateReviewAction(BaseModel):
    """Action to take on a duplicate pair."""
    action: str = Field(..., pattern="^(confirmed|dismissed)$")


class InvoiceParsedData(BaseModel):
    """Parsed data extracted from an invoice document."""
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "EUR"
    line_items: list = Field(default_factory=list)
    raw_text: str = ""

    @field_validator("total_amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError("Total amount cannot be negative")
        return v
