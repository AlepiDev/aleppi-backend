# routers/admin_professionals.py
from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from database import get_session
from auth.deps import get_current_admin
from models import Professional, User


router = APIRouter(prefix="/admin/professionals", tags=["admin-professionals"])


def _base_query():
    # Si luego quieres joins con User, puedes hacerlo aquí.
    return select(Professional).order_by(Professional.id.desc())


@router.get("/pending", response_model=List[Professional])
def list_pending_professionals(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    #_: User = Depends(get_current_admin),
):
    """
    Pendientes = Professional.active != True  (False o NULL)
    """
    stmt = _base_query().where(Professional.active.is_not(True))

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Professional.first_name.ilike(like))
            | (Professional.last_name.ilike(like))
            | (Professional.specialty.ilike(like))
            | (Professional.license_number.ilike(like))
        )

    stmt = stmt.offset(offset).limit(limit)
    return session.exec(stmt).all()


@router.get("/active", response_model=List[Professional])
def list_active_professionals(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    #_: User = Depends(get_current_admin),
):
    """
    Activos = Professional.active == True
    """
    stmt = _base_query().where(Professional.active.is_(True))

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Professional.first_name.ilike(like))
            | (Professional.last_name.ilike(like))
            | (Professional.specialty.ilike(like))
            | (Professional.license_number.ilike(like))
        )

    stmt = stmt.offset(offset).limit(limit)
    return session.exec(stmt).all()
