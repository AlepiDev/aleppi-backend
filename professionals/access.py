"""Chequeos de acceso/vigencia calculados al vuelo (sin cron/worker).

Vive separado de professionals/router.py y stripe_local/router.py para que
ambos lo puedan importar sin generar un ciclo (ninguno de los dos routers
importa del otro).
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from models import Professional, ProfessionalStatus, StripeSubscription


def has_active_period(db: Session, user_id: int, now: Optional[datetime] = None) -> bool:
    """True si el usuario tiene una StripeSubscription con current_period_end
    todavía en el futuro. Sin suscripción, o sin current_period_end, es False
    (no hay período de gracia por defecto)."""
    now = now or datetime.utcnow()

    subscription = db.exec(
        select(StripeSubscription)
        .where(
            StripeSubscription.user_id == user_id,
            StripeSubscription.current_period_end.is_not(None),
            StripeSubscription.current_period_end >= now,
        )
        .order_by(StripeSubscription.current_period_end.desc())
    ).first()

    return subscription is not None


def sync_professional_status(
    db: Session, professional: Professional, now: Optional[datetime] = None
) -> Professional:
    """Degrada Aprobado -> Suspendido cuando el período pagado ya venció.

    Es el inverso de _activate_professional (stripe_local/router.py): ese
    solo promueve al activarse una suscripción, este solo degrada al
    vencer. Nunca reactiva, para no pisar el flujo de aprobación manual.
    """
    if professional.status == ProfessionalStatus.aprobado.value and not has_active_period(
        db, professional.user_id, now=now
    ):
        professional.status = ProfessionalStatus.suspendido.value
        db.add(professional)
        db.commit()
        db.refresh(professional)

    return professional


def can_manage_profile(
    db: Session, professional: Professional, now: Optional[datetime] = None
) -> bool:
    """Regla de gracia tras un soft delete: el dueño conserva acceso a
    gestionar su perfil mientras tenga un período pagado vigente."""
    if professional.deleted_at is None:
        return True

    return has_active_period(db, professional.user_id, now=now)
