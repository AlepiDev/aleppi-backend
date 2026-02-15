# schema.py
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# -----------------------------
# Core blocks
# -----------------------------
class DashboardCards(BaseModel):
    """
    Cards principales del dashboard.
    Si algún cálculo falla y decides responder parcial, puedes regresar null.
    """

    pending_professionals: Optional[int] = Field(
        default=None, description="Solicitudes en espera de revisión"
    )
    active_professionals: Optional[int] = Field(
        default=None, description="Profesionales con membresía vigente"
    )
    month_income: Optional[float] = Field(
        default=None, description="Ingresos confirmados del mes (moneda del sistema)"
    )
    reports_last_7d: Optional[int] = Field(
        default=None, description="Contenido reportado en los últimos 7 días"
    )


class QuickSummary(BaseModel):
    """
    Bloque de 'Resumen rápido'. Ajusta o expande según tus métricas reales.
    """

    avg_professional_approval_hours: Optional[float] = Field(
        default=None, description="Tiempo promedio de aprobación (horas)"
    )
    membership_payments_confirmed_under_5m_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="% pagos confirmados en menos de 5 minutos",
    )
    articles_reported_at_least_once_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="% artículos reportados al menos una vez",
    )


# -----------------------------
# Partial error support
# -----------------------------
DashboardKey = Literal[
    "pending_professionals",
    "active_professionals",
    "month_income",
    "reports_last_7d",
    "quick_summary",
]


class DashboardError(BaseModel):
    key: DashboardKey = Field(..., description="Parte del dashboard que falló")
    message: str = Field(..., description="Descripción del error")
    code: Optional[str] = Field(default=None, description="Código de error interno")
    retryable: bool = Field(default=False, description="Si vale la pena reintentar")
    detail: Optional[str] = Field(
        default=None, description="Detalles técnicos (opcional)"
    )


# -----------------------------
# Final response DTO
# -----------------------------
class DashboardSummaryResponse(BaseModel):
    cards: DashboardCards
    quick_summary: Optional[QuickSummary] = None

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de generación de la respuesta (UTC)",
    )

    # Ej: '2026-02' o '2026-02-01..2026-02-11' según tu filtro
    period: Optional[str] = Field(
        default=None, description="Periodo usado para el cálculo"
    )

    # Lista de errores si respondes parcial
    errors: list[DashboardError] = Field(default_factory=list)
