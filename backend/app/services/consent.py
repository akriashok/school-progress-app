"""Parent consent (DPDP): show the school's current consent text; record acceptance."""

from sqlalchemy import select

from app.core.deps import Ctx
from app.core.errors import AppError, NotFound
from app.models import Consent, ConsentText, RoleType
from app.services import audit


class ConsentRequired(AppError):
    status_code = 403
    code = "CONSENT_REQUIRED"


def current_text(ctx: Ctx) -> ConsentText | None:
    return ctx.db.scalar(
        select(ConsentText).where(ConsentText.school_id == ctx.school_id, ConsentText.is_current.is_(True))
    )


def has_accepted(ctx: Ctx, text: ConsentText) -> bool:
    if ctx.user.guardian_id is None:
        return False
    return bool(
        ctx.db.scalar(
            select(Consent.id).where(
                Consent.school_id == ctx.school_id,
                Consent.guardian_id == ctx.user.guardian_id,
                Consent.consent_text_id == text.id,
                Consent.withdrawn_at.is_(None),
            )
        )
    )


def is_required(ctx: Ctx) -> bool:
    if ctx.user.role != RoleType.PARENT or ctx.user.school_id is None:
        return False
    text = current_text(ctx)
    return text is not None and not has_accepted(ctx, text)


def require_consent(ctx: Ctx) -> None:
    """Parents must accept the current consent text before seeing any child data."""
    if is_required(ctx):
        raise ConsentRequired("Please accept the consent statement to continue")


def accept(ctx: Ctx, version: int, user_agent: str | None) -> Consent:
    text = current_text(ctx)
    if text is None or text.version != version:
        raise NotFound("Current consent version")
    assert ctx.user.guardian_id is not None
    existing = ctx.db.scalar(
        select(Consent).where(
            Consent.guardian_id == ctx.user.guardian_id,
            Consent.consent_text_id == text.id,
            Consent.withdrawn_at.is_(None),
        )
    )
    if existing is not None:
        return existing
    c = Consent(
        school_id=ctx.school_id,
        guardian_id=ctx.user.guardian_id,
        consent_text_id=text.id,
        ip_address=ctx.ip,
        user_agent=(user_agent or "")[:300] or None,
    )
    ctx.db.add(c)
    ctx.db.flush()
    audit.record(ctx, audit.Action.CONSENT_ACCEPT, entity="consent", entity_id=c.id, new={"version": text.version})
    return c
