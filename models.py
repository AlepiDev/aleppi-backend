# models.py
# from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel


class UserBase(SQLModel):
    email: str = Field(index=True)
    role: int = Field(default=2)  # 1=admin, 2=profesional
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    admin_role: Optional[str] = Field(default=None)  # admin, super_admin, editor, soporte
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    professional: Optional["Professional"] = Relationship(
        sa_relationship=relationship(
            "Professional", back_populates="user", uselist=False
        )
    )

    stripe_customer: Optional["StripeCustomer"] = Relationship(
        sa_relationship=relationship(
            "StripeCustomer", back_populates="user", uselist=False
        )
    )

    stripe_subscriptions: list["StripeSubscription"] = Relationship(
        sa_relationship=relationship("StripeSubscription", back_populates="user")
    )


class ProfessionalBase(SQLModel):
    first_name: str
    last_name: str
    specialty: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[str] = None  # Comma-separated skills
    url_photo: Optional[str] = None
    years_experience: int = 0
    degree: Optional[str] = None
    license_number: Optional[str] = None
    license_file_path: Optional[str] = None
    state: str
    city: str
    mobile_phone: str
    active: bool = False
    status: str = "Inactivo"


class ProfessionalSocials(SQLModel, table=True):
    __tablename__ = "professional_socials"

    id: Optional[int] = Field(default=None, primary_key=True)
    professional_id: int = Field(
        foreign_key="professionals.id", index=True, unique=True
    )

    web: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None

    professional: "Professional" = Relationship(
        sa_relationship=relationship("Professional", back_populates="socials")
    )


class ProfessionalSchedule(SQLModel, table=True):
    __tablename__ = "professional_schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)

    day: str
    open: Optional[time] = None
    close: Optional[time] = None
    is_closed: bool = False

    professional: "Professional" = Relationship(
        sa_relationship=relationship("Professional", back_populates="schedules")
    )


class ProfessionalReview(SQLModel, table=True):
    __tablename__ = "professional_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)

    name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    professional: "Professional" = Relationship(
        sa_relationship=relationship("Professional", back_populates="reviews")
    )


class Professional(ProfessionalBase, table=True):
    __tablename__ = "professionals"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    user: "User" = Relationship(
        sa_relationship=relationship("User", back_populates="professional")
    )

    socials: Optional["ProfessionalSocials"] = Relationship(
        sa_relationship=relationship(
            "ProfessionalSocials", back_populates="professional", uselist=False
        )
    )

    schedules: List["ProfessionalSchedule"] = Relationship(
        sa_relationship=relationship(
            "ProfessionalSchedule", back_populates="professional"
        )
    )

    reviews: List["ProfessionalReview"] = Relationship(
        sa_relationship=relationship(
            "ProfessionalReview", back_populates="professional"
        )
    )

    addresses: List["ProfessionalAddress"] = Relationship(
        sa_relationship=relationship(
            "ProfessionalAddress", back_populates="professional"
        )
    )

    articles: List["Article"] = Relationship(
        sa_relationship=relationship("Article", back_populates="professional")
    )

    rejections: List["ProfessionalRejection"] = Relationship(
        sa_relationship=relationship(
            "ProfessionalRejection",
            back_populates="professional",
            order_by="ProfessionalRejection.created_at.desc()",
            cascade="all, delete-orphan",
        )
    )

    @property
    def rejection_reason(self) -> Optional[str]:
        """Último motivo de rechazo; sólo se muestra si está Rechazado."""
        if self.status != ProfessionalStatus.rechazado.value:
            return None
        if not self.rejections:
            return None
        return self.rejections[0].reason


# -------------------------
# Base mixins
# -------------------------
class TimestampMixin:
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": text("NOW()")},
    )


class UpdatedTimestampMixin:
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": text("NOW()")},
    )


# =====================================================
# Subscription plans (catalog)
# =====================================================
class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(nullable=False, unique=True)
    price_id: Optional[str] = Field(default=None, index=True, unique=True)


# =====================================================
# Stripe Events (idempotencia)
# =====================================================
class StripeEvent(SQLModel, table=True):
    __tablename__ = "stripe_events"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    stripe_event_id: str = Field(nullable=False, unique=True, index=True)
    type: str = Field(nullable=False, index=True)

    stripe_created: Optional[datetime] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    raw_json: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))


# =====================================================
# Stripe Customer
# =====================================================
class StripeCustomer(SQLModel, TimestampMixin, UpdatedTimestampMixin, table=True):
    __tablename__ = "stripe_customers"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    stripe_customer_id: str = Field(nullable=False, unique=True)
    email: Optional[str] = None

    user: "User" = Relationship(
        sa_relationship=relationship("User", back_populates="stripe_customer")
    )


# =====================================================
# Stripe Subscription
# =====================================================
class StripeSubscription(SQLModel, TimestampMixin, UpdatedTimestampMixin, table=True):
    __tablename__ = "stripe_subscriptions"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    user_id: int = Field(foreign_key="users.id", index=True)
    stripe_subscription_id: str = Field(nullable=False, unique=True)
    stripe_customer_id: str = Field(nullable=False, index=True)

    price_id: str
    status: str = Field(index=True)

    cancel_at_period_end: bool = False
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    transaction_id: Optional[str] = Field(default=None, index=True)
    user: "User" = Relationship(
        sa_relationship=relationship("User", back_populates="stripe_subscriptions")
    )


# =====================================================
# Stripe Invoice
# =====================================================
class StripeInvoice(SQLModel, TimestampMixin, table=True):
    __tablename__ = "stripe_invoices"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    stripe_invoice_id: str = Field(nullable=False, unique=True)
    stripe_customer_id: str = Field(nullable=False, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)

    amount_paid: Optional[int] = None
    amount_due: Optional[int] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    paid_at: Optional[datetime] = None

    raw_json: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )


# models.py (agrega esto)
class ProfessionalAddress(SQLModel, table=True):
    __tablename__ = "professional_addresses"

    id: Optional[int] = Field(default=None, primary_key=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)

    label: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_primary: Optional[bool] = True

    professional: "Professional" = Relationship(
        sa_relationship=relationship("Professional", back_populates="addresses")
    )


class ProfessionalRejection(SQLModel, table=True):
    __tablename__ = "professional_rejections"

    id: Optional[int] = Field(default=None, primary_key=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)
    reviewed_by: Optional[int] = Field(
        default=None, foreign_key="users.id", index=True
    )

    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    professional: "Professional" = Relationship(
        sa_relationship=relationship("Professional", back_populates="rejections")
    )


class ProfessionalStatus(str, Enum):
    inactivo = "Inactivo"
    pendiente = "Pendiente"
    aprobado = "Aprobado"
    suspendido = "Suspendido"
    rechazado = "Rechazado"


class ArticleStatus(str, Enum):
    pendiente = "Pendiente"
    drafted = "Drafted"
    aprobado = "Aprobado"
    rechazado = "Rechazado"


class CommentStatus(str, Enum):
    published = "published"
    blocked = "blocked"
    in_review = "in_review"


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    articles: List["Article"] = Relationship(
        sa_relationship=relationship(
            "Article", secondary="article_tag_links", back_populates="tags"
        )
    )


class ArticleTagLink(SQLModel, table=True):
    __tablename__ = "article_tag_links"

    article_id: Optional[int] = Field(
        default=None, foreign_key="articles.id", primary_key=True
    )
    tag_id: Optional[int] = Field(
        default=None, foreign_key="tags.id", primary_key=True
    )


class Article(SQLModel, table=True):
    __tablename__ = "articles"

    id: Optional[int] = Field(default=None, primary_key=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)

    title: str
    slug: str = Field(index=True, unique=True)
    header: Optional[str] = None  # base64-encoded image
    content: str

    status: ArticleStatus = Field(default=ArticleStatus.drafted, index=True)

    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    reviews_count: int = 0
    rating_avg: float = 0.0

    professional: "Professional" = Relationship(
        sa_relationship=relationship("Professional", back_populates="articles")
    )
    comments: List["ArticleComment"] = Relationship(
        sa_relationship=relationship("ArticleComment", back_populates="article")
    )
    reviews: List["ArticleReview"] = Relationship(
        sa_relationship=relationship("ArticleReview", back_populates="article")
    )
    tags: List["Tag"] = Relationship(
        sa_relationship=relationship(
            "Tag", secondary="article_tag_links", back_populates="articles"
        )
    )
    rejections: List["ArticleRejection"] = Relationship(
        sa_relationship=relationship(
            "ArticleRejection",
            back_populates="article",
            order_by="ArticleRejection.created_at.desc()",
            cascade="all, delete-orphan",
        )
    )

    @property
    def rejection_reason(self) -> Optional[str]:
        """Último motivo de rechazo; sólo se muestra si el artículo está rechazado."""
        if self.status != ArticleStatus.rechazado:
            return None
        if not self.rejections:
            return None
        return self.rejections[0].reason


class ArticleComment(SQLModel, table=True):
    __tablename__ = "article_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    content: str
    status: CommentStatus = Field(default=CommentStatus.in_review, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    article: "Article" = Relationship(
        sa_relationship=relationship("Article", back_populates="comments")
    )


class ArticleReview(SQLModel, table=True):
    __tablename__ = "article_reviews"

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    rating: int
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    article: "Article" = Relationship(
        sa_relationship=relationship("Article", back_populates="reviews")
    )


class ArticleRejection(SQLModel, table=True):
    __tablename__ = "article_rejections"

    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", index=True)
    reviewed_by: Optional[int] = Field(
        default=None, foreign_key="users.id", index=True
    )

    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    article: "Article" = Relationship(
        sa_relationship=relationship("Article", back_populates="rejections")
    )


class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)

    notify_email: bool = True
    notify_whatsapp: bool = False

    two_factor_enabled: bool = False

    language: str = "es"
    timezone: str = "America/Mexico_City"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
