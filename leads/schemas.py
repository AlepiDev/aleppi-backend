from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LeadCreate(BaseModel):
    nombre: str
    whatsapp: str
    email: EmailStr
    profesion: Optional[str] = None
    especialidad: Optional[str] = None
    plan: Optional[str] = None

    source: Optional[str] = None
    page: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None

    received_at: Optional[datetime] = Field(default=None, alias="receivedAt")

    model_config = ConfigDict(populate_by_name=True)


class LeadRead(BaseModel):
    id: UUID
    nombre: str
    whatsapp: str
    email: str
    profesion: Optional[str] = None
    especialidad: Optional[str] = None
    plan: Optional[str] = None

    source: Optional[str] = None
    page: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None

    received_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
