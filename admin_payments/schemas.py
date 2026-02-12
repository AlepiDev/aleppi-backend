# schemas/admin_payments.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentRow(BaseModel):
    invoice_id: UUID
    professional_id: int
    professional_name: str

    amount: float = Field(..., description="Monto en moneda (ej. MXN)")
    currency: Optional[str] = None

    date: Optional[datetime] = None
    status: str

    transaction_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


class PaymentsListResponse(BaseModel):
    items: list[PaymentRow]
    total: int
