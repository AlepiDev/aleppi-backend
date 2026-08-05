# routers/articles.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Article, ArticleRejection, Professional, Tag
from professionals.schemas import (
    ArticleCreate,
    ArticleRead,
    ArticleRejectRequest,
    ArticleStatusUpdate,
    ArticleUpdate,
)

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/professionals/{professional_id}/articles", tags=["articles"]
)


def _loggable_payload(data: dict) -> dict:
    """Copia del payload apta para log: trunca campos pesados (header/content)."""
    out = dict(data)
    if out.get("header"):
        out["header"] = f"<{len(out['header'])} chars>"
    if out.get("content"):
        out["content"] = f"<{len(out['content'])} chars>"
    return out


def _resolve_tags(session: Session, tag_names: list[str]) -> list[Tag]:
    """Return Tag objects for the given names, creating them if they don't exist."""
    tags = []
    for name in tag_names:
        tag = session.exec(select(Tag).where(Tag.name == name)).first()
        if not tag:
            tag = Tag(name=name)
            session.add(tag)
            session.flush()
        tags.append(tag)
    return tags


@router.post("/", response_model=ArticleRead, status_code=201)
def create_article(
    professional_id: int,
    payload: ArticleCreate,
    session: Session = Depends(get_session),
):
    logger.info(
        "POST /professionals/%s/articles payload: %s",
        professional_id,
        _loggable_payload(payload.model_dump()),
    )

    if not session.get(Professional, professional_id):
        raise HTTPException(404, "Profesional no encontrado")

    exists = session.exec(select(Article).where(Article.slug == payload.slug)).first()
    if exists:
        raise HTTPException(400, "slug ya existe")

    data = payload.model_dump(exclude={"tags"})
    article = Article(professional_id=professional_id, **data)
    if (
        getattr(article, "status", None) == "Aprobado"
        and getattr(article, "published_at", None) is None
    ):
        article.published_at = datetime.utcnow()

    article.tags = _resolve_tags(session, payload.tags)
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


@router.get("/", response_model=List[ArticleRead])
def list_articles(
    professional_id: int,
    session: Session = Depends(get_session),
    status_: Optional[str] = None,
):
    stmt = (
        select(Article)
        .where(Article.professional_id == professional_id)
        .order_by(Article.created_at.desc())
    )
    if status_:
        stmt = stmt.where(Article.status == status_)
    return session.exec(stmt).all()


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(
    professional_id: int, article_id: int, session: Session = Depends(get_session)
):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")
    return article


@router.patch("/{article_id}", response_model=ArticleRead)
def update_article(
    professional_id: int,
    article_id: int,
    payload: ArticleUpdate,
    session: Session = Depends(get_session),
):
    logger.info(
        "PATCH /professionals/%s/articles/%s payload: %s",
        professional_id,
        article_id,
        _loggable_payload(payload.model_dump(exclude_unset=True)),
    )

    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")

    data = payload.model_dump(exclude_unset=True, exclude={"tags"})
    for k, v in data.items():
        setattr(article, k, v)

    if payload.tags is not None:
        article.tags = _resolve_tags(session, payload.tags)

    if (
        data.get("status") == "Aprobado"
        and getattr(article, "published_at", None) is None
    ):
        article.published_at = datetime.utcnow()

    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


@router.patch("/{article_id}/status", response_model=ArticleRead)
def update_article_status(
    professional_id: int,
    article_id: int,
    payload: ArticleStatusUpdate,
    session: Session = Depends(get_session),
):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")

    article.status = payload.status
    if payload.status == "Aprobado" and article.published_at is None:
        article.published_at = datetime.utcnow()

    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


@router.patch("/{article_id}/reject", response_model=ArticleRead)
def reject_article(
    professional_id: int,
    article_id: int,
    payload: ArticleRejectRequest,
    session: Session = Depends(get_session),
):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")

    article.status = "Rechazado"
    article.published_at = None
    article.updated_at = datetime.utcnow()

    rejection = ArticleRejection(
        article_id=article.id,
        reason=payload.reason.strip(),
    )

    session.add(article)
    session.add(rejection)
    session.commit()
    session.refresh(article)
    return article


@router.delete("/{article_id}", status_code=204)
def delete_article(
    professional_id: int, article_id: int, session: Session = Depends(get_session)
):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")

    session.delete(article)
    session.commit()
    return


