# routers/admin_memberships.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from auth.deps import get_current_admin
from database import get_session
from models import (
    Professional,
    StripeCustomer,
    StripeInvoice,
    StripeSubscription,
    User,
)

from .schemas import MembershipRead, MembershipsListResponse

router = APIRouter(prefix="/admin", tags=["admin-memberships"])


def _sub_to_read(sub: StripeSubscription, prof: Optional[Professional]) -> MembershipRead:
    prof_id = prof.id if prof else None
    prof_name = None
    if prof:
        prof_name = " ".join([p for p in [prof.first_name, prof.last_name] if p]) or None
    return MembershipRead(
        id=sub.id,
        stripe_subscription_id=sub.stripe_subscription_id,
        stripe_customer_id=sub.stripe_customer_id,
        price_id=sub.price_id,
        status=sub.status,
        cancel_at_period_end=sub.cancel_at_period_end,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        canceled_at=sub.canceled_at,
        professional_id=prof_id,
        professional_name=prof_name,
    )


@router.get("/memberships", response_model=MembershipsListResponse)
def list_memberships(
    status: Optional[str] = None,
    price_id: Optional[str] = None,
    renewal_from: Optional[date] = None,
    renewal_to: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
):
    stmt = (
        select(StripeSubscription, Professional)
        .join(Professional, Professional.user_id == StripeSubscription.user_id, isouter=True)
    )

    if status:
        stmt = stmt.where(StripeSubscription.status == status)
    if price_id:
        stmt = stmt.where(StripeSubscription.price_id == price_id)
    if renewal_from:
        stmt = stmt.where(
            StripeSubscription.current_period_end >= datetime.combine(renewal_from, datetime.min.time())
        )
    if renewal_to:
        stmt = stmt.where(
            StripeSubscription.current_period_end <= datetime.combine(renewal_to, datetime.max.time())
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(session.exec(total_stmt).one())

    stmt = stmt.order_by(StripeSubscription.current_period_end.desc()).offset(offset).limit(limit)
    rows = session.exec(stmt).all()

    items = [_sub_to_read(sub, prof) for sub, prof in rows]
    return MembershipsListResponse(items=items, total=total)


@router.get("/memberships/last-by-user", response_model=MembershipsListResponse)
def list_last_subscription_per_user(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
):
    """Última suscripción de cada usuario, sin importar el status."""
    # DISTINCT ON (user_id) ordenado por fecha de creación desc => la más reciente.
    latest = (
        select(StripeSubscription)
        .distinct(StripeSubscription.user_id)
        .order_by(
            StripeSubscription.user_id,
            StripeSubscription.created_at.desc(),
        )
        .subquery()
    )
    latest_sub = aliased(StripeSubscription, latest)

    total = int(session.exec(select(func.count()).select_from(latest)).one())

    stmt = (
        select(latest_sub, Professional)
        .join(
            Professional,
            Professional.user_id == latest_sub.user_id,
            isouter=True,
        )
        .order_by(latest_sub.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = session.exec(stmt).all()

    items = [_sub_to_read(sub, prof) for sub, prof in rows]
    return MembershipsListResponse(items=items, total=total)


@router.get("/memberships/{membership_id}", response_model=MembershipRead)
def get_membership(
    membership_id: UUID,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
):
    sub = session.get(StripeSubscription, membership_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Membresía no encontrada")

    prof = session.exec(
        select(Professional).where(Professional.user_id == sub.user_id)
    ).first()

    return _sub_to_read(sub, prof)


@router.get("/customers/{customer_id}/membership", response_model=MembershipRead)
def get_customer_membership(
    customer_id: int,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
):
    """Membresía activa de un cliente (customer_id = user_id)."""
    sub = session.exec(
        select(StripeSubscription)
        .where(StripeSubscription.user_id == customer_id)
        .order_by(StripeSubscription.current_period_end.desc())
    ).first()

    if not sub:
        raise HTTPException(status_code=404, detail="El cliente no tiene membresía")

    prof = session.exec(
        select(Professional).where(Professional.user_id == customer_id)
    ).first()

    return _sub_to_read(sub, prof)


@router.get("/customers/{customer_id}/payments")
def get_customer_payments(
    customer_id: int,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
):
    """Historial de pagos (invoices) de un cliente por su user_id."""
    customer = session.exec(
        select(StripeCustomer).where(StripeCustomer.user_id == customer_id)
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    stmt = (
        select(StripeInvoice)
        .where(StripeInvoice.stripe_customer_id == customer.stripe_customer_id)
        .order_by(StripeInvoice.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    total_stmt = select(func.count()).select_from(
        select(StripeInvoice)
        .where(StripeInvoice.stripe_customer_id == customer.stripe_customer_id)
        .subquery()
    )
    total = int(session.exec(total_stmt).one())
    invoices = session.exec(stmt).all()

    return {
        "total": total,
        "items": [
            {
                "invoice_id": str(inv.id),
                "stripe_invoice_id": inv.stripe_invoice_id,
                "amount": float((inv.amount_paid or inv.amount_due or 0) / 100),
                "currency": inv.currency,
                "status": inv.status,
                "created_at": inv.created_at,
                "paid_at": inv.paid_at,
            }
            for inv in invoices
        ],
    }
