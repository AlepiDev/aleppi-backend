# routers/dashboard.py
import shutil
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from passlib.context import CryptContext
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Professional, User

from .schemas import DashboardCards, DashboardSummaryResponse, QuickSummary

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin_dashboard", tags=["admin_dashboard"])


def count_active_professionals(session: Session) -> int:
    stmt = (
        select(func.count())
        .select_from(Professional)
        .where(Professional.active.is_(True))
    )
    return int(session.exec(stmt).one())


def count_pending_professionals(session: Session) -> int:
    # pending = active != True  => False o NULL
    stmt = (
        select(func.count())
        .select_from(Professional)
        .where(Professional.active.is_not(True))
    )
    return int(session.exec(stmt).one())


@router.post("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(session: Session = Depends(get_session)):

    active = count_active_professionals(session)
    pending = count_pending_professionals(session)
    return DashboardSummaryResponse(
        cards=DashboardCards(
            pending_professionals=pending,
            active_professionals=active,
            month_income=48500.0,
            reports_last_7d=5,
        ),
        quick_summary=QuickSummary(
            avg_professional_approval_hours=12,
            membership_payments_confirmed_under_5m_pct=93,
            articles_reported_at_least_once_pct=4,
        ),
        period="2026-02",
        errors=[],
    )
