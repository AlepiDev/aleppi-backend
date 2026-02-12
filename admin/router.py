# routers/admin_users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from pydantic import BaseModel, EmailStr  # 👈 ESTE IMPORT

from database import get_session
from models import User, Professional
from auth.schemas import UserRead
from auth.router import get_password_hash
from auth.deps import get_current_admin
from sqlalchemy import func

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str


router = APIRouter(prefix="/admin/users", tags=["admin-users"])

def count_active_professionals(session: Session) -> int:
    stmt = select(func.count()).select_from(Professional).where(Professional.active.is_(True))
    return int(session.exec(stmt).one())


def count_pending_professionals(session: Session) -> int:
    # pending = active != True  => False o NULL
    stmt = select(func.count()).select_from(Professional).where(Professional.active.is_not(True))
    return int(session.exec(stmt).one())

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),  # 👈 sólo admins
):
    existing = session.exec(
        select(User).where(User.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=1,           # 👈 admin
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
