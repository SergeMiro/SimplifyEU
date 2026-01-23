from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Literal
from uuid import UUID

class Analysis(BaseModel):
    id: UUID
    account_id: UUID
    user_id: UUID
    status: Literal['pending', 'processing', 'completed', 'failed']
    source_type: str = 'csv'
    filename: Optional[str] = None
    file_url: Optional[str] = None
    total_transactions: Optional[int] = None
    subscriptions_found: int = 0
    potential_savings_eur: float = 0
    report_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class AnalysisItem(BaseModel):
    id: UUID
    analysis_id: UUID
    merchant_descriptor: str
    merchant_name: Optional[str] = None
    category: Optional[str] = None
    amount_avg: float
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    currency: str = 'EUR'
    frequency: Optional[Literal['weekly', 'biweekly', 'monthly', 'quarterly', 'annual', 'irregular']] = None
    occurrences: int
    first_seen: date
    last_seen: date
    confidence_score: Optional[float] = None
    is_subscription: bool = False
    tags: List[str] = []
    recommendation: Optional[str] = None
    created_at: datetime

class Transaction(BaseModel):
    date: date
    description: str
    amount: float
    currency: str = "EUR"
