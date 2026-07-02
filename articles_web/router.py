# routers/articles.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import math
from fastapi import Query
from sqlmodel import select, func
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Article, Professional
from professionals.schemas import ArticleRead, PaginatedArticles

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/articles", tags=["articles"]
)



@router.get("/", response_model=PaginatedArticles)
def list_articles(
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    #base_where = (Article.status == "Aprobado")

    # total_items
    total_items = session.exec(
        select(func.count()).select_from(Article)
    ).one()

    total_pages = max(1, math.ceil(total_items / page_size))
    offset = (page - 1) * page_size

    # items paginados
    stmt = (
        select(Article)
        #.where(base_where)
        .order_by(Article.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = session.exec(stmt).all()

    return {
        "items": items,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
    }


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: int, session: Session = Depends(get_session)):
    article = session.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    return article
