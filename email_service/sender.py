"""Envío de emails transaccionales vía Resend.

Contrato: nunca debe propagar excepciones. Pensado para ejecutarse tanto
directo como dentro de un BackgroundTasks de FastAPI, donde un error sin
capturar solo terminaría en el log del proceso sin forma de reportarlo
al request que ya respondió.
"""
import os

import resend

from utils.logging import get_logger

logger = get_logger(__name__)


def _init_resend() -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY no configurada; no se puede enviar email.")
        return False

    resend.api_key = api_key
    return True


def send_rejection_email(to_email: str, professional_name: str, reason: str) -> None:
    """Notifica a un profesional que su perfil fue rechazado, con el motivo."""
    try:
        if not _init_resend():
            return

        from_email = os.getenv("RESEND_FROM_EMAIL")
        if not from_email:
            logger.error("RESEND_FROM_EMAIL no configurada; no se puede enviar email.")
            return

        resend.Emails.send(
            {
                "from": from_email,
                "to": [to_email],
                "subject": "Tu perfil profesional no fue aprobado",
                "html": (
                    f"<p>Hola {professional_name},</p>"
                    f"<p>Tu perfil profesional en Aleppi no fue aprobado por el "
                    f"siguiente motivo:</p>"
                    f"<p><strong>{reason}</strong></p>"
                    f"<p>Puedes corregir tu información y volver a enviarla para "
                    f"revisión.</p>"
                ),
            }
        )
        logger.info("Email de rechazo enviado a %s", to_email)
    except Exception:
        logger.exception("Error enviando email de rechazo a %s", to_email)
