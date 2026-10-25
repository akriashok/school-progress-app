"""Content of a school's public website. Images are ids of files uploaded to our own
storage (never external URLs, so the public page loads nothing from third parties)."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, field_validator

from app.services.phone import normalize_phone

IMAGE_ID_PATTERN = r"^[0-9a-f]{32}\.(png|jpg|webp)$"

ImageId = Annotated[str, Field(pattern=IMAGE_ID_PATTERN)]
Short = Annotated[str, Field(max_length=120)]
Long = Annotated[str, Field(max_length=2000)]


def _https(v: str | None) -> str | None:
    if v in (None, ""):
        return None
    if not v.startswith("https://") or len(v) > 300 or any(c.isspace() for c in v):
        raise ValueError("must be an https:// link")
    return v


HttpsUrl = Annotated[str | None, AfterValidator(_https)]
Icon = Literal["bus", "music", "playground", "book", "computer", "heart", "trophy", "flask", "palette", "shield"]


class Card(BaseModel):
    title: Short
    body: Long = ""
    image: ImageId | None = None


class Facility(BaseModel):
    title: Short
    body: Long = ""
    icon: Icon = "book"
    image: ImageId | None = None


class StatItem(BaseModel):
    value: Annotated[str, Field(max_length=12)]
    label: Annotated[str, Field(max_length=40)]


class GalleryItem(BaseModel):
    image: ImageId
    caption: Short = ""


class Leader(BaseModel):
    name: Short
    role: Short = ""
    bio: Long = ""
    photo: ImageId | None = None


class Admissions(BaseModel):
    open: bool = False
    title: Short = ""
    body: Long = ""


class Contact(BaseModel):
    whatsapp: str | None = None
    facebook: HttpsUrl = None
    instagram: HttpsUrl = None
    youtube: HttpsUrl = None
    map_url: HttpsUrl = None
    timings: Short = ""

    @field_validator("whatsapp")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else None


class Theme(BaseModel):
    primary: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")] = "#1f4e79"
    accent: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")] = "#f59e0b"


class WebsiteContent(BaseModel):
    tagline: Short = ""
    hero_title: Short = ""
    hero_subtitle: Long = ""
    hero_image: ImageId | None = None
    about_title: Short = ""
    about_body: Annotated[str, Field(max_length=5000)] = ""
    about_image: ImageId | None = None
    highlights: Annotated[list[Card], Field(max_length=6)] = []
    facilities: Annotated[list[Facility], Field(max_length=8)] = []
    stats: Annotated[list[StatItem], Field(max_length=4)] = []
    gallery: Annotated[list[GalleryItem], Field(max_length=24)] = []
    leaders: Annotated[list[Leader], Field(max_length=8)] = []
    excellence: Annotated[list[Short], Field(max_length=10)] = []
    admissions: Admissions = Admissions()
    contact: Contact = Contact()
    theme: Theme = Theme()


class PublicWebsite(BaseModel):
    code: str
    name: str
    board: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    phone: str | None
    email: str | None
    has_logo: bool
    website: WebsiteContent


class ImageUploaded(BaseModel):
    image_id: str
