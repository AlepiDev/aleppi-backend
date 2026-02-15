# routers/article_comments.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Article, ArticleComment
from professionals.schemas import CommentCreate, CommentRead, CommentUpdate

router = APIRouter(prefix="/articles/{article_id}/comments", tags=["article-comments"])


@router.post("/", response_model=CommentRead, status_code=201)
def create_comment(
    article_id: int,
    payload: CommentCreate,
    session: Session = Depends(get_session),
):
    if not session.get(Article, article_id):
        raise HTTPException(status_code=404, detail="Artículo no encontrado")

    row = ArticleComment(
        article_id=article_id,
        content=payload.content,
        # status por default: in_review (según tu modelo)
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/", response_model=List[CommentRead])
def list_comments(
    article_id: int,
    session: Session = Depends(get_session),
    status_: Optional[str] = None,
):
    stmt = (
        select(ArticleComment)
        .where(ArticleComment.article_id == article_id)
        .order_by(ArticleComment.created_at.desc())
    )
    if status_:
        stmt = stmt.where(ArticleComment.status == status_)
    return session.exec(stmt).all()


@router.patch("/{comment_id}", response_model=CommentRead)
def update_comment(
    article_id: int,
    comment_id: int,
    payload: CommentUpdate,
    session: Session = Depends(get_session),
):
    row = session.get(ArticleComment, comment_id)
    if not row or row.article_id != article_id:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)

    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{comment_id}", status_code=204)
def delete_comment(
    article_id: int,
    comment_id: int,
    session: Session = Depends(get_session),
):
    row = session.get(ArticleComment, comment_id)
    if not row or row.article_id != article_id:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")

    session.delete(row)
    session.commit()
    return
