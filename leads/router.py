from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlmodel import Session, select

from auth.deps import get_current_admin
from database import get_session
from leads.schemas import LeadCreate, LeadRead
from models import Lead, User

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["leads"])


@router.post("/leads", response_model=LeadRead, status_code=201)
def create_lead(
    payload: LeadCreate,
    request: Request,
    session: Session = Depends(get_session),
    x_request_id: Optional[str] = Header(default=None, alias="x-request-id"),
):
    # Reintentos del mismo submit (mismo x-request-id) devuelven el lead ya
    # creado en vez de duplicarlo.
    if x_request_id:
        existing = session.exec(
            select(Lead).where(Lead.request_id == x_request_id)
        ).first()
        if existing:
            return existing

    row = Lead(
        nombre=payload.nombre,
        whatsapp=payload.whatsapp,
        email=payload.email,
        profesion=payload.profesion,
        especialidad=payload.especialidad,
        plan=payload.plan,
        source=payload.source,
        page=payload.page,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        utm_term=payload.utm_term,
        received_at=payload.received_at,
        request_id=x_request_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    logger.info("Nuevo lead: %s (%s) source=%s plan=%s", row.nombre, row.email, row.source, row.plan)

    return row


admin_router = APIRouter(prefix="/admin/leads", tags=["admin-leads"])


@admin_router.get("/", response_model=List[LeadRead])
def list_leads(
    q: Optional[str] = None,
    plan: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
):
    stmt = select(Lead).order_by(Lead.created_at.desc())

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Lead.nombre.ilike(like))
            | (Lead.email.ilike(like))
            | (Lead.whatsapp.ilike(like))
        )
    if plan:
        stmt = stmt.where(Lead.plan == plan)
    if source:
        stmt = stmt.where(Lead.source == source)

    stmt = stmt.offset(offset).limit(limit)
    return session.exec(stmt).all()
