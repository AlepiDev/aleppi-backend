# routers/professionals.py
from __future__ import annotations

from typing import List
import logging
from uuid import uuid4
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sqlalchemy import update

from passlib.context import CryptContext

from database import get_session
from models import User, Professional, ProfessionalSocials, ProfessionalSchedule, ProfessionalAddress
from professionals.schemas import (
    ProfessionalRead, ProfessionalStatusUpdate,
    ProfessionalSocialsUpsert, ProfessionalSocialsRead,
    ProfessionalScheduleCreate, ProfessionalScheduleUpdate, ProfessionalScheduleRead,
    ProfessionalAddressCreate, ProfessionalAddressUpdate, ProfessionalAddressRead,
)

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
    years_experience: int = Form(0),
    degree: str = Form(None),
    license_number: str = Form(None),
    state: str = Form(...),
    city: str = Form(...),
    mobile_phone: str = Form(...),
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

    uploads_dir = Path("uploads/licenses")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(license_file.filename).suffix
    file_name = f"{uuid4().hex}{ext}"
    file_path = uploads_dir / file_name
    with file_path.open("wb") as f:
        shutil.copyfileobj(license_file.file, f)

    professional = Professional(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        specialty=specialty,
        years_experience=years_experience,
        degree=degree,
        license_number=license_number,
        license_file_path=str(file_path),
        state=state,
        city=city,
        mobile_phone=mobile_phone,
    )
    session.add(professional)
    session.commit()
    session.refresh(professional)
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
    years_experience: int = Form(0),
    degree: str = Form(None),
    license_number: str = Form(None),
    state: str = Form(...),
    city: str = Form(...),
    mobile_phone: str = Form(...),
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

    if license_file is not None:
        uploads_dir = Path("uploads/licenses")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(license_file.filename).suffix
        file_name = f"{uuid4().hex}{ext}"
        file_path = uploads_dir / file_name

        with file_path.open("wb") as f:
            shutil.copyfileobj(license_file.file, f)

        professional.license_file_path = str(file_path)

    professional.first_name = first_name
    professional.last_name = last_name
    professional.specialty = specialty
    professional.years_experience = years_experience
    professional.degree = degree
    professional.license_number = license_number
    professional.state = state
    professional.city = city
    professional.mobile_phone = mobile_phone

    session.add(professional)
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

    professional.active = payload.active
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
        select(ProfessionalSocials).where(ProfessionalSocials.professional_id == professional_id)
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
        select(ProfessionalSocials).where(ProfessionalSocials.professional_id == professional_id)
    ).first()
    if not socials:
        raise HTTPException(status_code=404, detail="Socials no encontrados")
    return socials


# ---------- Schedules (1:N) ----------
@router.get("/{professional_id}/schedules", response_model=List[ProfessionalScheduleRead])
def list_schedules(professional_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(ProfessionalSchedule)
        .where(ProfessionalSchedule.professional_id == professional_id)
        .order_by(ProfessionalSchedule.day.asc())
    ).all()


@router.post("/{professional_id}/schedules", response_model=ProfessionalScheduleRead, status_code=201)
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


@router.patch("/{professional_id}/schedules/{schedule_id}", response_model=ProfessionalScheduleRead)
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
def delete_schedule(professional_id: int, schedule_id: int, session: Session = Depends(get_session)):
    row = session.get(ProfessionalSchedule, schedule_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Schedule no encontrado")

    session.delete(row)
    session.commit()
    return


# ---------- Addresses (1:N) ----------
@router.get("/{professional_id}/addresses", response_model=List[ProfessionalAddressRead])
def list_addresses(professional_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(ProfessionalAddress)
        .where(ProfessionalAddress.professional_id == professional_id)
        .order_by(ProfessionalAddress.is_primary.desc(), ProfessionalAddress.id.desc())
    ).all()


@router.post("/{professional_id}/addresses", response_model=ProfessionalAddressRead, status_code=201)
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


@router.patch("/{professional_id}/addresses/{address_id}", response_model=ProfessionalAddressRead)
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


@router.post("/{professional_id}/addresses/{address_id}/make-primary", response_model=ProfessionalAddressRead)
def make_primary_address(professional_id: int, address_id: int, session: Session = Depends(get_session)):
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
def delete_address(professional_id: int, address_id: int, session: Session = Depends(get_session)):
    row = session.get(ProfessionalAddress, address_id)
    if not row or row.professional_id != professional_id:
        raise HTTPException(status_code=404, detail="Address no encontrado")

    session.delete(row)
    session.commit()
    return
