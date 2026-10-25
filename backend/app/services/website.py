"""School public website: content editing (school admin) and public reads."""

import re
import uuid

from sqlalchemy.orm import Session

from app.core.deps import Ctx
from app.core.errors import NotFound, ValidationFailed
from app.models import School
from app.schemas.website import IMAGE_ID_PATTERN, PublicWebsite, WebsiteContent
from app.services.schools import get_own_school, public_school
from app.services.storage import get_storage

MAX_IMAGE_BYTES = 3 * 1024 * 1024
_IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_MIME = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def _key(school_id: uuid.UUID, image_id: str) -> str:
    # The school id is part of the key, so one school's code can never serve another's files.
    return f"site/{school_id}/{image_id}"


def default_content(school: School) -> WebsiteContent:
    """Sensible starting content so a new school's page looks complete before editing."""
    return WebsiteContent(
        tagline=f"Welcome to {school.name}",
        hero_title="Nurturing curious minds",
        hero_subtitle="A caring school where every child learns, plays and grows with confidence.",
        about_title=f"About {school.name}",
        about_body=(
            "We combine strong academics with sports, arts and values. Small classes and dedicated teachers "
            "help every child reach their potential."
        ),
        highlights=[
            {"title": "Academics", "body": "A balanced curriculum with regular assessments and feedback."},
            {"title": "Activities", "body": "Sports, music, dance and clubs for every interest."},
            {"title": "Values", "body": "Respect, honesty and kindness in everything we do."},
        ],
        facilities=[
            {"title": "Smart classrooms", "icon": "computer", "body": "Bright, well-equipped classrooms."},
            {"title": "Library", "icon": "book", "body": "Books for every age and reading level."},
            {"title": "Play area", "icon": "playground", "body": "Safe outdoor and indoor play spaces."},
            {"title": "Transport", "icon": "bus", "body": "School buses covering the city."},
        ],
        stats=[],
    )


def get_content(ctx: Ctx) -> WebsiteContent:
    school = get_own_school(ctx)
    return WebsiteContent.model_validate(school.website) if school.website else default_content(school)


def save_content(ctx: Ctx, content: WebsiteContent) -> WebsiteContent:
    school = get_own_school(ctx)
    storage = get_storage()
    missing = [img for img in _images(content) if not storage.exists(_key(school.id, img))]
    if missing:
        raise ValidationFailed("Some images were not found; upload them again", details=missing)
    school.website = content.model_dump(mode="json")
    ctx.db.flush()
    return content


def _images(c: WebsiteContent) -> list[str]:
    found = [c.hero_image, c.about_image]
    found += [h.image for h in c.highlights] + [f.image for f in c.facilities]
    found += [g.image for g in c.gallery] + [lead.photo for lead in c.leaders]
    return [i for i in found if i]


def upload_image(ctx: Ctx, content: bytes, content_type: str) -> str:
    ext = _IMAGE_TYPES.get(content_type)
    if ext is None:
        raise ValidationFailed("Upload a PNG, JPEG or WebP image")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValidationFailed("Images must be under 3 MB")
    ok = (
        (ext == "png" and content.startswith(b"\x89PNG"))
        or (ext == "jpg" and content.startswith(b"\xff\xd8"))
        or (ext == "webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP")
    )
    if not ok:
        raise ValidationFailed("The file is not a valid image")
    image_id = f"{uuid.uuid4().hex}.{ext}"
    get_storage().put(_key(ctx.school_id, image_id), content, content_type)
    return image_id


def public_website(db: Session, code: str) -> PublicWebsite:
    school = public_school(db, code)
    content = WebsiteContent.model_validate(school.website) if school.website else default_content(school)
    return PublicWebsite(
        code=school.code,
        name=school.name,
        board=school.board,
        address=school.address,
        city=school.city,
        state=school.state,
        pincode=school.pincode,
        phone=school.phone,
        email=school.email,
        has_logo=bool(school.logo_url),
        website=content,
    )


def public_image(db: Session, code: str, image_id: str) -> tuple[bytes, str]:
    if not re.fullmatch(IMAGE_ID_PATTERN, image_id):
        raise NotFound("Image")
    school = public_school(db, code)
    data = get_storage().get(_key(school.id, image_id))
    if data is None:
        raise NotFound("Image")
    return data, _MIME[image_id.rsplit(".", 1)[1]]
