from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserSettingsRead(BaseModel):
    id: UUID
    user_id: int
    notify_email: bool
    notify_whatsapp: bool
    two_factor_enabled: bool
    language: str
    timezone: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(BaseModel):
    notify_email: Optional[bool] = None
    notify_whatsapp: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
