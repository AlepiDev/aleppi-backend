from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MembershipRead(BaseModel):
    id: UUID
    stripe_subscription_id: str
    stripe_customer_id: str
    price_id: str
    status: str
    cancel_at_period_end: bool
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    professional_id: Optional[int] = None
    professional_name: Optional[str] = None


class MembershipsListResponse(BaseModel):
    items: list[MembershipRead]
    total: int
