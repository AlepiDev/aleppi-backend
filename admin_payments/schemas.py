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


class UserPaymentsHistoryResponse(BaseModel):
    user_id: int
    professional_id: Optional[int] = None
    professional_name: Optional[str] = None
    email: Optional[str] = None
    customer_id: Optional[str] = None

    payments_count: int
    total_paid: float = Field(..., description="Suma de pagos en moneda (ej. MXN)")
    currency: Optional[str] = None

    items: list[PaymentRow]
    total: int


class PaymentDetail(BaseModel):
    invoice_id: UUID
    professional_id: Optional[int] = None
    professional_name: Optional[str] = None
    customer_id: Optional[str] = None

    amount: float
    currency: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None

    stripe_invoice_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    transaction_id: Optional[str] = None

    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
