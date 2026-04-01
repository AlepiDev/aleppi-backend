# routers/professionals.py
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from passlib.context import CryptContext
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from database import get_session
from models import (Professional, ProfessionalAddress, ProfessionalSchedule,
                    ProfessionalSocials, User)
from professionals.schemas import (ProfessionalAddressCreate,
                                   ProfessionalAddressRead,
                                   ProfessionalAddressUpdate, ProfessionalRead,
                                   ProfessionalScheduleCreate,
                                   ProfessionalScheduleRead,
                                   ProfessionalScheduleUpdate,
                                   ProfessionalSocialsRead,
                                   ProfessionalSocialsUpsert,
                                   ProfessionalStatusUpdate)
from storage import storage_service

logger = logging.getLogger("app")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/professionals", tags=["professionals"])


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


@router.post("/", response_model=ProfessionalRead, status_code=status.HTTP_201_CREATED)
async def create_professional(
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    specialty: str = Form(...),
    short_description: str = Form(None),
    description: str = Form(None),
    skills: str = Form(None),
    years_experience: int = Form(0),
    degree: str = Form(None),
    license_number: str = Form(None),
    state: str = Form(...),
    city: str = Form(...),
    mobile_phone: str = Form(...),
    professional_status: str = Form("Inactivo"),
    schedules: str = Form(None),
    photo_file: UploadFile | None = File(None),
    license_file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(email=email, hashed_password=get_password_hash(password), role=2)
    session.add(user)
    session.commit()
    session.refresh(user)

    # Upload photo to Azure Blob Storage
    url_photo = None
    if photo_file is not None:
        url_photo = await storage_service.upload_file(photo_file, "uploads/photos")

    # Upload license file to Azure Blob Storage
    license_file_path = await storage_service.upload_file(license_file, "uploads/licenses")

    professional = Professional(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        specialty=specialty,
        short_description=short_description,
        description=description,
        skills=skills,
        url_photo=url_photo,
        years_experience=years_experience,
        degree=degree,
        license_number=license_number,
        license_file_path=license_file_path,
        state=state,
        city=city,
        mobile_phone=mobile_phone,
        status=professional_status,
    )
    session.add(professional)
    session.commit()
    session.refresh(professional)

    # Create schedules if provided
    if schedules is not None:
        try:
            schedules_data = json.loads(schedules)
            for schedule_item in schedules_data:
                new_schedule = ProfessionalSchedule(
                    professional_id=professional.id,
                    day=schedule_item.get("day"),
                    open=schedule_item.get("open"),
                    close=schedule_item.get("close"),
                    is_closed=schedule_item.get("is_closed", False)
                )
                session.add(new_schedule)
            session.commit()
        except json.JSONDecodeError:
            logger.error("Error parsing schedules JSON")

    return professional


@router.get("/", response_model=List[ProfessionalRead])
def list_professionals(session: Session = Depends(get_session)):
    stmt = select(Professional).options(selectinload(Professional.user))
    professionals = session.exec(stmt).all()
    logger.info("professionals=%s", len(professionals))
    return professionals


@router.get("/{professional_id}", response_model=ProfessionalRead)
def get_professional(professional_id: int, session: Session = Depends(get_session)):
    stmt = (
        select(Professional)
        .where(Professional.id == professional_id)
        .options(selectinload(Professional.user))
    )
    professional = session.exec(stmt).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return professional


@router.put("/{professional_id}", response_model=ProfessionalRead)
async def update_professional(
    professional_id: int,
    email: str = Form(...),
    password: str = Form(None),
    first_name: str = Form(...),
    last_name: str = Form(...),
    specialty: str = Form(...),
    short_description: str = Form(None),
    description: str = Form(None),
    skills: str = Form(None),
    years_experience: int = Form(0),
    degree: str = Form(None),
    license_number: str = Form(None),
    state: str = Form(...),
    city: str = Form(...),
    mobile_phone: str = Form(...),
    professional_status: str = Form(None),
    web: str = Form(None),
    facebook: str = Form(None),
    instagram: str = Form(None),
    youtube: str = Form(None),
    schedule: str = Form(None),
    url_photo: UploadFile | None = File(None),
    license_file: UploadFile | None = File(None),
    session: Session = Depends(get_session),
):
    professional = session.get(Professional, professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    user = session.get(User, professional.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.email = email
    if password:
        user.hashed_password = get_password_hash(password)
    session.add(user)

    if url_photo is not None and url_photo.filename:
        professional.url_photo = await storage_service.upload_file(
            url_photo, "uploads/photos"
        )

    if license_file is not None and license_file.filename:
        professional.license_file_path = await storage_service.upload_file(
            license_file, "uploads/licenses"
        )

    professional.first_name = first_name
    professional.last_name = last_name
    professional.specialty = specialty
    professional.short_description = short_description
    professional.description = description
    professional.skills = skills
    professional.years_experience = years_experience
    professional.degree = degree
    professional.license_number = license_number
    professional.state = state
    professional.city = city
    professional.mobile_phone = mobile_phone
    if professional_status is not None:
        professional.status = professional_status
    session.add(professional)

    # Upsert socials
    socials = session.exec(
        select(ProfessionalSocials).where(
            ProfessionalSocials.professional_id == professional_id
        )
    ).first()

    if socials is None:
        socials = ProfessionalSocials(professional_id=professional_id)

    socials.web = web
    socials.facebook = facebook
    socials.instagram = instagram
    socials.youtube = youtube
    session.add(socials)

    # Upsert schedules
    if schedule is not None:
        try:
            schedules_data = json.loads(schedule)

            # Eliminar schedules existentes
            existing_schedules = session.exec(
                select(ProfessionalSchedule).where(
                    ProfessionalSchedule.professional_id == professional_id
                )
            ).all()
            for sch in existing_schedules:
                session.delete(sch)

            # Crear nuevos schedules
            for schedule_item in schedules_data:
                new_schedule = ProfessionalSchedule(
                    professional_id=professional_id,
                    day=schedule_item.get("day"),
                    open=schedule_item.get("start") or schedule_item.get("open"),
                    close=schedule_item.get("end") or schedule_item.get("close"),
                    is_closed=schedule_item.get("is_closed", False)
                )
                session.add(new_schedule)
        except json.JSONDecodeError:
            logger.error("Error parsing schedules JSON")

    session.commit()
    session.refresh(professional)
    return professional


@router.delete("/{professional_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_professional(professional_id: int, session: Session = Depends(get_session)):
    professional = session.get(Professional, professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    user = session.get(User, professional.user_id)
    if user:
        session.delete(user)
    session.delete(professional)
    session.commit()
    return


@router.patch("/{professional_id}/status", response_model=ProfessionalRead)
def update_professional_status(
    professional_id: int,
    payload: ProfessionalStatusUpdate,
    session: Session = Depends(get_session),
):
    professional = session.get(Professional, professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    if payload.active is not None:
        professional.active = payload.active
    if payload.status is not None:
        professional.status = payload.status
    session.add(professional)
    session.commit()
    session.refresh(professional)
    return professional


# ---------- Socials (1:1) ----------
@router.put("/{professional_id}/socials", response_model=ProfessionalSocialsRead)
def upsert_socials(
    professional_id: int,
    payload: ProfessionalSocialsUpsert,
    session: Session = Depends(get_session),
):
    if not session.get(Professional, professional_id):
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    socials = session.exec(
        select(ProfessionalSocials).where(
            ProfessionalSocials.professional_id == professional_id
        )
    ).first()

    if socials is None:
        socials = ProfessionalSocials(professional_id=professional_id)

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(socials, k, v)

    session.add(socials)
    session.commit()
    session.refresh(socials)
    return socials


@router.get("/{professional_id}/socials", response_model=ProfessionalSocialsRead)
def get_socials(professional_id: int, session: Session = Depends(get_session)):
    socials = session.exec(
        select(ProfessionalSocials).where(
            ProfessionalSocials.professional_id == professional_id
        )
    ).first()
    if not socials:
        raise HTTPException(status_code=404, detail="Socials no encontrados")
    return socials


# ---------- Schedules (1:N) ----------
@router.get(
    "/{professional_id}/schedules", response_model=List[ProfessionalScheduleRead]
)
def list_schedules(professional_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(ProfessionalSchedule)
        .where(ProfessionalSchedule.professional_id == professional_id)
        .order_by(ProfessionalSchedule.day.asc())
    ).all()


@router.post(
    "/{professional_id}/schedules",
    response_model=ProfessionalScheduleRead,
    status_code=201,
)
def create_schedule(
    professional_id: int,
    payload: ProfessionalScheduleCreate,
    session: Session = Depends(get_session),
):
    if not session.get(Professional, professional_id):
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    row = ProfessionalSchedule(professional_id=professional_id, **payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch(
    "/{professional_id}/schedules/{schedule_id}",
    response_model=ProfessionalScheduleRead,
)
def update_schedule(
    professional_id: int,
    schedule_id: int,
    payload: ProfessionalScheduleUpdate,
    session: Session = Depends(get_session),
):
    row = session.get(ProfessionalSchedule, schedule_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Schedule no encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{professional_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    professional_id: int, schedule_id: int, session: Session = Depends(get_session)
):
    row = session.get(ProfessionalSchedule, schedule_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Schedule no encontrado")

    session.delete(row)
    session.commit()
    return


# ---------- Addresses (1:N) ----------
@router.get(
    "/{professional_id}/addresses", response_model=List[ProfessionalAddressRead]
)
def list_addresses(professional_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(ProfessionalAddress)
        .where(ProfessionalAddress.professional_id == professional_id)
        .order_by(ProfessionalAddress.is_primary.desc(), ProfessionalAddress.id.desc())
    ).all()


@router.post(
    "/{professional_id}/addresses",
    response_model=ProfessionalAddressRead,
    status_code=201,
)
def create_address(
    professional_id: int,
    payload: ProfessionalAddressCreate,
    session: Session = Depends(get_session),
):
    if not session.get(Professional, professional_id):
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    if payload.is_primary:
        session.exec(
            update(ProfessionalAddress)
            .where(ProfessionalAddress.professional_id == professional_id)
            .values(is_primary=False)
        )

    row = ProfessionalAddress(professional_id=professional_id, **payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch(
    "/{professional_id}/addresses/{address_id}", response_model=ProfessionalAddressRead
)
def update_address(
    professional_id: int,
    address_id: int,
    payload: ProfessionalAddressUpdate,
    session: Session = Depends(get_session),
):
    row = session.get(ProfessionalAddress, address_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Address no encontrado")

    data = payload.model_dump(exclude_unset=True)

    if data.get("is_primary") is True:
        session.exec(
            update(ProfessionalAddress)
            .where(
                (ProfessionalAddress.professional_id == professional_id)
                & (ProfessionalAddress.id != address_id)
            )
            .values(is_primary=False)
        )

    for k, v in data.items():
        setattr(row, k, v)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.post(
    "/{professional_id}/addresses/{address_id}/make-primary",
    response_model=ProfessionalAddressRead,
)
def make_primary_address(
    professional_id: int, address_id: int, session: Session = Depends(get_session)
):
    row = session.get(ProfessionalAddress, address_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Address no encontrado")

    session.exec(
        update(ProfessionalAddress)
        .where(ProfessionalAddress.professional_id == professional_id)
        .values(is_primary=False)
    )

    row.is_primary = True
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{professional_id}/addresses/{address_id}", status_code=204)
def delete_address(
    professional_id: int, address_id: int, session: Session = Depends(get_session)
):
    row = session.get(ProfessionalAddress, address_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Address no encontrado")

    session.delete(row)
    session.commit()
    return
