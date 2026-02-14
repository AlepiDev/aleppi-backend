# routers/articles.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Professional, Article
from professionals.schemas import ArticleCreate, ArticleUpdate, ArticleRead

router = APIRouter(prefix="/professionals/{professional_id}/articles", tags=["articles"])


@router.post("/", response_model=ArticleRead, status_code=201)
def create_article(professional_id: int, payload: ArticleCreate, session: Session = Depends(get_session)):
    if not session.get(Professional, professional_id):
        raise HTTPException(404, "Profesional no encontrado")

    exists = session.exec(select(Article).where(Article.slug == payload.slug)).first()
    if exists:
        raise HTTPException(400, "slug ya existe")

    article = Article(professional_id=professional_id, **payload.model_dump())
    if getattr(article, "status", None) == "published" and getattr(article, "published_at", None) is None:
        article.published_at = datetime.utcnow()

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
    stmt = select(Article).where(Article.professional_id == professional_id).order_by(Article.created_at.desc())
    if status_:
        stmt = stmt.where(Article.status == status_)
    return session.exec(stmt).all()


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(professional_id: int, article_id: int, session: Session = Depends(get_session)):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")
    return article


@router.patch("/{article_id}", response_model=ArticleRead)
def update_article(professional_id: int, article_id: int, payload: ArticleUpdate, session: Session = Depends(get_session)):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(article, k, v)

    if data.get("status") == "published" and getattr(article, "published_at", None) is None:
        article.published_at = datetime.utcnow()

    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


@router.delete("/{article_id}", status_code=204)
def delete_article(professional_id: int, article_id: int, session: Session = Depends(get_session)):
    article = session.get(Article, article_id)
    if not article or article.professional_id != professional_id:
        raise HTTPException(404, "Artículo no encontrado")

    session.delete(article)
    session.commit()
    return
