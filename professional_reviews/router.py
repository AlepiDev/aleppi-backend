# routers/professional_reviews.py
from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from article_reviews.router import recompute_professional_metrics
from database import get_session
from models import Professional, ProfessionalReview
from professionals.schemas import (
    ProfessionalReviewAdminRead,
    ProfessionalReviewApprovalUpdate,
    ProfessionalReviewCreate,
    ProfessionalReviewRead,
)

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/professionals/{professional_id}/reviews", tags=["professional-reviews"]
)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def _get_professional_or_404(session: Session, professional_id: int) -> Professional:
    professional = session.get(Professional, professional_id)
    if not professional:
        raise HTTPException(404, "Profesional no encontrado")
    return professional


def _get_review_or_404(
    session: Session, professional_id: int, review_id: int
) -> ProfessionalReview:
    row = session.get(ProfessionalReview, review_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(404, "Reseña no encontrada")
    return row


def _verify_turnstile(token: str, remote_ip: str | None) -> None:
    secret = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
    if not secret:
        raise HTTPException(500, "Falta TURNSTILE_SECRET_KEY.")

    try:
        resp = httpx.post(
            TURNSTILE_VERIFY_URL,
            data={"secret": secret, "response": token, "remoteip": remote_ip},
            timeout=10,
        )
        result = resp.json()
    except httpx.HTTPError:
        raise HTTPException(502, "No se pudo verificar el captcha.")

    if not result.get("success"):
        raise HTTPException(400, "Verificación de captcha inválida.")


@router.get("/")
def list_professional_reviews(
    professional_id: int,
    session: Session = Depends(get_session),
):
    """Public listing: only approved reviews, privacy-safe fields."""
    _get_professional_or_404(session, professional_id)

    rows = session.exec(
        select(ProfessionalReview)
        .where(ProfessionalReview.professional_id == professional_id)
        .order_by(ProfessionalReview.created_at.desc())
    ).all()

    return {
        "success": True,
        "data": [ProfessionalReviewRead.model_validate(row) for row in rows],
    }


@router.post("/", status_code=201)
def create_professional_review(
    professional_id: int,
    payload: ProfessionalReviewCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    _get_professional_or_404(session, professional_id)
    _verify_turnstile(
        payload.turnstile_token, request.client.host if request.client else None
    )

    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(400, "rating debe ser 1..5")

    row = ProfessionalReview(
        professional_id=professional_id,
        name=payload.name,
        email=payload.email,
        rating=payload.rating,
        comment=payload.comment,
        approved=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    recompute_professional_metrics(session, professional_id)
    session.commit()

    return {"success": True, "data": ProfessionalReviewAdminRead.model_validate(row)}


@router.put("/{review_id}")
def update_professional_review(
    professional_id: int,
    review_id: int,
    payload: ProfessionalReviewCreate,
    session: Session = Depends(get_session),
):
    row = _get_review_or_404(session, professional_id, review_id)

    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(400, "rating debe ser 1..5")

    row.name = payload.name
    row.email = payload.email
    row.rating = payload.rating
    row.comment = payload.comment
    session.add(row)
    session.commit()
    session.refresh(row)

    recompute_professional_metrics(session, professional_id)
    session.commit()

    return {"success": True, "data": ProfessionalReviewAdminRead.model_validate(row)}


@router.patch("/{review_id}/approve")
def set_professional_review_approval(
    professional_id: int,
    review_id: int,
    payload: ProfessionalReviewApprovalUpdate,
    session: Session = Depends(get_session),
):
    row = _get_review_or_404(session, professional_id, review_id)

    row.approved = payload.approved
    session.add(row)
    session.commit()
    session.refresh(row)

    recompute_professional_metrics(session, professional_id)
    session.commit()

    return {"success": True, "data": ProfessionalReviewAdminRead.model_validate(row)}


@router.delete("/{review_id}")
def delete_professional_review(
    professional_id: int,
    review_id: int,
    session: Session = Depends(get_session),
):
    row = _get_review_or_404(session, professional_id, review_id)

    session.delete(row)
    session.commit()

    recompute_professional_metrics(session, professional_id)
    session.commit()

    return {"success": True}
