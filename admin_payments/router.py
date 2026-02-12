# routers/admin_payments.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from sqlalchemy import func

from auth.deps import get_current_admin
from database import get_session
from models import User, Professional, StripeInvoice, StripeSubscription

from .schemas import PaymentsListResponse, PaymentRow


router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


def _money_from_cents(cents: Optional[int]) -> float:
    return float((cents or 0) / 100)


@router.get("/history", response_model=PaymentsListResponse)
def payments_history(
    q: Optional[str] = None,
    status: Optional[str] = Query(default=None, description="Ej: paid, open, uncollectible, void, draft"),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    #_: User = Depends(get_current_admin),
) -> PaymentsListResponse:
    """
    Historial basado en StripeInvoice.
    Une invoice -> subscription (opcional) -> user_id -> professional para nombre.
    """

    stmt = (
        select(
            StripeInvoice,
            Professional.id,
            Professional.first_name,
            Professional.last_name,
            StripeSubscription.stripe_subscription_id,
            StripeSubscription.transaction_id,
        )
        # link invoice -> subscription (si existe)
        .join(
            StripeSubscription,
            StripeSubscription.stripe_subscription_id == StripeInvoice.stripe_subscription_id,
            isouter=True,
        )
        # link subscription.user_id -> professional.user_id
        .join(
            Professional,
            Professional.user_id == StripeSubscription.user_id,
            isouter=True,
        )
    )

    # Filtros de fecha usando paid_at si existe; si no, usa created_at
    if from_date or to_date:
        start_dt = datetime.combine(from_date or date.today() - timedelta(days=3650), datetime.min.time())
        end_dt = datetime.combine(to_date or date.today(), datetime.max.time())
        stmt = stmt.where(
            func.coalesce(StripeInvoice.paid_at, StripeInvoice.created_at).between(start_dt, end_dt)
        )

    if status:
        stmt = stmt.where(StripeInvoice.status == status)

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Professional.first_name.ilike(like))
            | (Professional.last_name.ilike(like))
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(session.exec(total_stmt).one())

    stmt = stmt.order_by(StripeInvoice.created_at.desc()).offset(offset).limit(limit)
    rows = session.exec(stmt).all()

    items: list[PaymentRow] = []
    for inv, prof_id, first, last, sub_id, tx_id in rows:
        prof_name = " ".join([p for p in [first, last] if p]) if first or last else "(Sin profesional)"
        items.append(
            PaymentRow(
                invoice_id=inv.id,
                professional_id=prof_id or 0,
                professional_name=prof_name,
                amount=_money_from_cents(inv.amount_paid or inv.amount_due),
                currency=inv.currency,
                date=inv.paid_at or inv.created_at,
                status=inv.status or "unknown",
                transaction_id=tx_id,
                stripe_invoice_id=inv.stripe_invoice_id,
                stripe_subscription_id=sub_id,
            )
        )

    return PaymentsListResponse(items=items, total=total)


@router.post("/invoices/{invoice_id}/confirm", response_model=PaymentRow)
def confirm_payment(
    invoice_id: str,
    session: Session = Depends(get_session),
    #_: User = Depends(get_current_admin),
):
    inv = session.get(StripeInvoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice no encontrada")

    if inv.status == "paid":
        raise HTTPException(status_code=400, detail="La invoice ya está pagada")

    inv.status = "paid"
    inv.amount_paid = inv.amount_paid or inv.amount_due
    inv.paid_at = inv.paid_at or datetime.utcnow()

    session.add(inv)
    session.commit()
    session.refresh(inv)

    # Respuesta simple sin join (puedes reusar el join si quieres)
    return PaymentRow(
        invoice_id=inv.id,
        professional_id=0,
        professional_name="",
        amount=_money_from_cents(inv.amount_paid or inv.amount_due),
        currency=inv.currency,
        date=inv.paid_at or inv.created_at,
        status=inv.status or "paid",
        transaction_id=None,
        stripe_invoice_id=inv.stripe_invoice_id,
        stripe_subscription_id=inv.stripe_subscription_id,
    )
