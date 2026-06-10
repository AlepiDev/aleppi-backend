# routers/admins.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from auth.deps import get_current_admin
from auth.router import get_password_hash
from database import get_session
from models import User

router = APIRouter(prefix="/admins", tags=["admins"])

VALID_ADMIN_ROLES = {"admin", "super_admin", "editor", "soporte"}


class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    role: Optional[str] = "admin"
    actor_type: Optional[str] = None


class AdminUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    actor_type: Optional[str] = None


class AdminRead(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    admin_role: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminListResponse(BaseModel):
    items: List[AdminRead]
    total: int


@router.get("/", response_model=AdminListResponse)
def list_admins(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    q: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
):
    stmt = select(User).where(User.role == 1)

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (User.email.ilike(like))
            | (User.first_name.ilike(like))
            | (User.last_name.ilike(like))
        )
    if role:
        stmt = stmt.where(User.admin_role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    total_stmt = select(User.id).where(User.role == 1)
    total = len(session.exec(total_stmt).all())

    offset = (page - 1) * limit
    stmt = stmt.order_by(User.id.desc()).offset(offset).limit(limit)
    items = session.exec(stmt).all()

    return AdminListResponse(items=items, total=total)


@router.post("/", response_model=AdminRead, status_code=status.HTTP_201_CREATED)
def create_admin(
    payload: AdminCreate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
):
    if payload.role and payload.role not in VALID_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role debe ser uno de: {', '.join(VALID_ADMIN_ROLES)}",
        )

    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_active=payload.is_active,
        role=1,
        admin_role=payload.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/{admin_id}", response_model=AdminRead)
def update_admin(
    admin_id: int,
    payload: AdminUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
):
    user = session.get(User, admin_id)
    if not user or user.role != 1:
        raise HTTPException(status_code=404, detail="Admin no encontrado")

    if payload.role and payload.role not in VALID_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role debe ser uno de: {', '.join(VALID_ADMIN_ROLES)}",
        )

    if payload.email is not None:
        conflict = session.exec(
            select(User).where(User.email == payload.email, User.id != admin_id)
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="El email ya está en uso")
        user.email = payload.email

    if payload.password is not None:
        user.hashed_password = get_password_hash(payload.password)
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.admin_role = payload.role

    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin(
    admin_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
):
    user = session.get(User, admin_id)
    if not user or user.role != 1:
        raise HTTPException(status_code=404, detail="Admin no encontrado")

    user.is_active = False
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
