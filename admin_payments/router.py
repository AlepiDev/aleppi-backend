# routers/admin_payments.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
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

from .schemas import (
    PaymentDetail,
    PaymentRow,
    PaymentsListResponse,
    UserPaymentsHistoryResponse,
)

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


def _money_from_cents(cents: Optional[int]) -> float:
    return float((cents or 0) / 100)


def _build_payments_query(
    q: Optional[str],
    status: Optional[str],
    from_date: Optional[date],
    to_date: Optional[date],
    customer_id: Optional[str],
    professional_id: Optional[int],
    subscription_id: Optional[str],
):
    stmt = (
        select(
            StripeInvoice,
            Professional.id,
            Professional.first_name,
            Professional.last_name,
            StripeSubscription.stripe_subscription_id,
            StripeSubscription.transaction_id,
        )
        .join(
            StripeSubscription,
            StripeSubscription.stripe_subscription_id
            == StripeInvoice.stripe_subscription_id,
            isouter=True,
        )
        .join(
            Professional,
            Professional.user_id == StripeSubscription.user_id,
            isouter=True,
        )
    )

    if from_date or to_date:
        start_dt = datetime.combine(
            from_date or date.today() - timedelta(days=3650), datetime.min.time()
        )
        end_dt = datetime.combine(to_date or date.today(), datetime.max.time())
        stmt = stmt.where(
            func.coalesce(StripeInvoice.paid_at, StripeInvoice.created_at).between(
                start_dt, end_dt
            )
        )

    if status:
        stmt = stmt.where(StripeInvoice.status == status)

    if customer_id:
        stmt = stmt.where(StripeInvoice.stripe_customer_id == customer_id)

    if subscription_id:
        stmt = stmt.where(StripeInvoice.stripe_subscription_id == subscription_id)

    if professional_id:
        stmt = stmt.where(Professional.id == professional_id)

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Professional.first_name.ilike(like))
            | (Professional.last_name.ilike(like))
            | (StripeInvoice.stripe_invoice_id.ilike(like))
        )

    return stmt


@router.get("/", response_model=PaymentsListResponse)
def list_payments(
    q: Optional[str] = None,
    status: Optional[str] = Query(
        default=None, description="Ej: paid, open, uncollectible, void, draft"
    ),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    customer_id: Optional[str] = None,
    professional_id: Optional[int] = None,
    subscription_id: Optional[str] = None,
    sort: Optional[str] = Query(default="created_at:desc", description="Ej: created_at:desc"),
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
) -> PaymentsListResponse:
    stmt = _build_payments_query(q, status, from_date, to_date, customer_id, professional_id, subscription_id)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(session.exec(total_stmt).one())

    stmt = stmt.order_by(StripeInvoice.created_at.desc()).offset(offset).limit(limit)
    rows = session.exec(stmt).all()

    items = _rows_to_payment_list(rows)
    return PaymentsListResponse(items=items, total=total)


@router.get("/history", response_model=UserPaymentsHistoryResponse)
def payments_history(
    user_id: int = Query(..., description="ID del usuario del que se obtiene el historial"),
    status: Optional[str] = Query(default=None),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
) -> UserPaymentsHistoryResponse:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    customer = session.exec(
        select(StripeCustomer).where(StripeCustomer.user_id == user_id)
    ).first()
    customer_id = customer.stripe_customer_id if customer else None

    prof = session.exec(
        select(Professional).where(Professional.user_id == user_id)
    ).first()
    professional_id = prof.id if prof else None
    professional_name = (
        " ".join([p for p in [prof.first_name, prof.last_name] if p]) or None
        if prof
        else None
    )

    email = (customer.email if customer and customer.email else None) or user.email

    # Sin customer de Stripe el usuario no tiene pagos registrados.
    if not customer_id:
        return UserPaymentsHistoryResponse(
            user_id=user_id,
            professional_id=professional_id,
            professional_name=professional_name,
            email=email,
            customer_id=None,
            payments_count=0,
            total_paid=0.0,
            currency=None,
            items=[],
            total=0,
        )

    stmt = _build_payments_query(
        None, status, from_date, to_date, customer_id, None, None
    )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(session.exec(total_stmt).one())

    sum_stmt = select(
        func.coalesce(
            func.sum(
                func.coalesce(StripeInvoice.amount_paid, StripeInvoice.amount_due)
            ),
            0,
        )
    ).select_from(stmt.subquery())
    total_paid = _money_from_cents(int(session.exec(sum_stmt).one()))

    stmt = stmt.order_by(StripeInvoice.created_at.desc()).offset(offset).limit(limit)
    rows = session.exec(stmt).all()
    items = _rows_to_payment_list(rows)

    currency = next((i.currency for i in items if i.currency), None)

    return UserPaymentsHistoryResponse(
        user_id=user_id,
        professional_id=professional_id,
        professional_name=professional_name,
        email=email,
        customer_id=customer_id,
        payments_count=total,
        total_paid=total_paid,
        currency=currency,
        items=items,
        total=total,
    )


@router.get("/{payment_id}", response_model=PaymentDetail)
def get_payment_detail(
    payment_id: UUID,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
) -> PaymentDetail:
    inv = session.get(StripeInvoice, payment_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    prof_id = None
    prof_name = None
    tx_id = None

    sub = session.exec(
        select(StripeSubscription).where(
            StripeSubscription.stripe_subscription_id == inv.stripe_subscription_id
        )
    ).first()

    if sub:
        tx_id = sub.transaction_id
        prof = session.exec(
            select(Professional).where(Professional.user_id == sub.user_id)
        ).first()
        if prof:
            prof_id = prof.id
            prof_name = " ".join([p for p in [prof.first_name, prof.last_name] if p]) or None

    failure_reason = None
    if inv.raw_json:
        failure_reason = inv.raw_json.get("failure_reason") or inv.raw_json.get("failure_message")

    return PaymentDetail(
        invoice_id=inv.id,
        professional_id=prof_id,
        professional_name=prof_name,
        customer_id=inv.stripe_customer_id,
        amount=_money_from_cents(inv.amount_paid or inv.amount_due),
        currency=inv.currency,
        status=inv.status or "unknown",
        failure_reason=failure_reason,
        stripe_invoice_id=inv.stripe_invoice_id,
        stripe_subscription_id=inv.stripe_subscription_id,
        transaction_id=tx_id,
        created_at=inv.created_at,
        paid_at=inv.paid_at,
    )


@router.post("/invoices/{invoice_id}/confirm", response_model=PaymentRow)
def confirm_payment(
    invoice_id: str,
    session: Session = Depends(get_session),
    # _: User = Depends(get_current_admin),
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


def _rows_to_payment_list(rows) -> list[PaymentRow]:
    items: list[PaymentRow] = []
    for inv, prof_id, first, last, sub_id, tx_id in rows:
        prof_name = (
            " ".join([p for p in [first, last] if p]) if first or last else "(Sin profesional)"
        )
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
    return items
