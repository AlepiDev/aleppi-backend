from datetime import datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from auth.schemas import UserRead


class ProfessionalSocialsRead(BaseModel):
    web: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ProfessionalScheduleRead(BaseModel):
    day: str
    open: Optional[time] = None
    close: Optional[time] = None
    model_config = ConfigDict(from_attributes=True)


class ProfessionalReviewRead(BaseModel):
    id: int
    user: Optional[str] = None  # si luego quieres nombre, aquí lo llenas
    rating: int
    comment: Optional[str] = None
    date: datetime


class ProfessionalCreate(BaseModel):
    # Datos de usuario
    email: EmailStr
    password: str

    # Datos de perfil profesional (form de la imagen)
    first_name: str
    last_name: str
    specialty: str
    description: Optional[str] = None
    skills: Optional[str] = None  # Comma-separated skills
    url_photo: Optional[str] = None
    years_experience: int = 0
    degree: Optional[str] = None
    license_number: Optional[str] = None
    state: str
    city: str
    mobile_phone: str


class ProfessionalRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    specialty: str
    description: Optional[str]
    skills: Optional[str]  # Comma-separated skills
    url_photo: Optional[str]
    years_experience: int
    degree: Optional[str]
    license_number: Optional[str]
    license_file_path: Optional[str]
    state: str
    city: str
    mobile_phone: str
    user: UserRead

    rating: Optional[float] = None
    reviews: List[ProfessionalReviewRead] = []
    address: Optional[str] = None
    socials: Optional[ProfessionalSocialsRead] = None
    schedule: List[ProfessionalScheduleRead] = []

    model_config = ConfigDict(from_attributes=True)


class ProfessionalStatusUpdate(BaseModel):
    active: bool


class ProfessionalSocialsUpsert(BaseModel):
    web: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None


class ProfessionalSocialsRead(BaseModel):
    web: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# -------- Schedules --------
class ProfessionalScheduleCreate(BaseModel):
    day: str
    open: Optional[time] = None
    close: Optional[time] = None
    is_closed: bool = False


class ProfessionalScheduleUpdate(BaseModel):
    open: Optional[time] = None
    close: Optional[time] = None
    is_closed: Optional[bool] = None


class ProfessionalScheduleRead(BaseModel):
    id: int
    day: str
    open: Optional[time] = None
    close: Optional[time] = None
    is_closed: bool
    model_config = ConfigDict(from_attributes=True)


# -------- Addresses --------
class ProfessionalAddressCreate(BaseModel):
    label: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_primary: Optional[bool] = True


class ProfessionalAddressUpdate(BaseModel):
    label: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_primary: Optional[bool] = None


class ProfessionalAddressRead(BaseModel):
    id: int
    label: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_primary: Optional[bool] = True
    model_config = ConfigDict(from_attributes=True)


from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ArticleStatus(str, Enum):
    draft = "draft"
    published = "published"
    inactive = "inactive"


class CommentStatus(str, Enum):
    published = "published"
    blocked = "blocked"
    in_review = "in_review"


class ArticleCreate(BaseModel):
    title: str
    slug: str
    content: str
    status: ArticleStatus = ArticleStatus.draft


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    status: Optional[ArticleStatus] = None


class ArticleStatusUpdate(BaseModel):
    status: ArticleStatus


class ArticleRead(BaseModel):
    id: int
    professional_id: int
    title: str
    slug: str
    content: str
    status: ArticleStatus
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    reviews_count: int
    rating_avg: float
    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[CommentStatus] = None


class CommentRead(BaseModel):
    id: int
    article_id: int
    user_id: Optional[int] = None
    content: str
    status: CommentStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ArticleReviewCreate(BaseModel):
    rating: int  # 1..5
    comment: Optional[str] = None


class ArticleReviewRead(BaseModel):
    id: int
    article_id: int
    user_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedArticles(BaseModel):
    items: List[ArticleRead]
    total_pages: int
    page: int
    page_size: int
    total_items: int
