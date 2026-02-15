# routers/article_reviews.py
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Article, ArticleReview, Professional, ProfessionalReview
from professionals.schemas import ArticleReviewCreate, ArticleReviewRead

router = APIRouter(prefix="/articles/{article_id}/reviews", tags=["article-reviews"])


def recompute_article_metrics(session: Session, article_id: int) -> None:
    reviews_count = int(
        session.exec(
            select(func.count())
            .select_from(ArticleReview)
            .where(ArticleReview.article_id == article_id)
        ).one()
    )
    rating_avg = float(
        session.exec(
            select(func.coalesce(func.avg(ArticleReview.rating), 0)).where(
                ArticleReview.article_id == article_id
            )
        ).one()
    )

    article = session.get(Article, article_id)
    if article:
        article.reviews_count = reviews_count
        article.rating_avg = rating_avg
        article.updated_at = datetime.utcnow()
        session.add(article)


def recompute_professional_metrics(session: Session, professional_id: int) -> None:
    reviews_count = int(
        session.exec(
            select(func.count())
            .select_from(ProfessionalReview)
            .where(ProfessionalReview.professional_id == professional_id)
        ).one()
    )
    rating_avg = float(
        session.exec(
            select(func.coalesce(func.avg(ProfessionalReview.rating), 0)).where(
                ProfessionalReview.professional_id == professional_id
            )
        ).one()
    )

    prof = session.get(Professional, professional_id)
    if prof:
        prof.reviews_count = reviews_count
        prof.rating_avg = rating_avg
        session.add(prof)


@router.post("/", response_model=ArticleReviewRead, status_code=201)
def create_article_review(
    article_id: int,
    payload: ArticleReviewCreate,
    session: Session = Depends(get_session),
):
    article = session.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")

    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(400, "rating debe ser 1..5")

    row = ArticleReview(
        article_id=article_id, rating=payload.rating, comment=payload.comment
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    recompute_article_metrics(session, article_id)
    recompute_professional_metrics(session, article.professional_id)
    session.commit()

    return row
