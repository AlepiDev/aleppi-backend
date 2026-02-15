from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import UserSettings
from users.schemas import UserSettingsRead, UserSettingsUpdate

router = APIRouter(prefix="/me", tags=["me"])


def get_current_user():
    # aquí va tu auth real (JWT)
    ...


@router.get("/settings", response_model=UserSettingsRead)
def get_my_settings(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

    return settings


@router.patch("/settings", response_model=UserSettingsRead)
def update_my_settings(
    payload: UserSettingsUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(settings, k, v)

    settings.updated_at = datetime.utcnow()
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings
