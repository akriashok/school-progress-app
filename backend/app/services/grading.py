"""Grading rules (DESIGN.md §8). Pure functions so they're easy to test by hand."""

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GradeBand, GradeScale

CBSE_DEFAULT_NAME = "CBSE 8-point"
CBSE_BANDS: list[tuple[str, str, str, str]] = [
    # grade, min %, max %, grade point
    ("A1", "91", "100", "10"),
    ("A2", "81", "90.99", "9"),
    ("B1", "71", "80.99", "8"),
    ("B2", "61", "70.99", "7"),
    ("C1", "51", "60.99", "6"),
    ("C2", "41", "50.99", "5"),
    ("D", "33", "40.99", "4"),
    ("E", "0", "32.99", "0"),
]


@dataclass(frozen=True)
class Band:
    grade: str
    min_percent: Decimal
    max_percent: Decimal


def round2(v: Decimal | float | int) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def grade_for(percentage: Decimal | None, bands: list[Band]) -> str | None:
    if percentage is None:
        return None
    p = round2(percentage)
    for b in sorted(bands, key=lambda b: b.min_percent, reverse=True):
        if p >= b.min_percent:
            return b.grade
    return None


def pass_marks_for(max_marks: Decimal, pass_marks: Decimal | None, pass_percent: Decimal) -> Decimal:
    return pass_marks if pass_marks is not None else max_marks * pass_percent / Decimal(100)


def create_default_scale(db: Session, school_id: uuid.UUID) -> GradeScale:
    scale = GradeScale(school_id=school_id, name=CBSE_DEFAULT_NAME, is_default=True)
    db.add(scale)
    db.flush()
    for grade, lo, hi, gp in CBSE_BANDS:
        db.add(
            GradeBand(
                grade_scale_id=scale.id,
                grade=grade,
                min_percent=Decimal(lo),
                max_percent=Decimal(hi),
                grade_point=Decimal(gp),
            )
        )
    db.flush()
    return scale


def load_bands(db: Session, school_id: uuid.UUID, grade_scale_id: uuid.UUID | None) -> list[Band]:
    scale_id = grade_scale_id or db.scalar(
        select(GradeScale.id).where(GradeScale.school_id == school_id, GradeScale.is_default.is_(True))
    )
    if scale_id is None:
        return []
    rows = db.scalars(
        select(GradeBand)
        .join(GradeScale, GradeScale.id == GradeBand.grade_scale_id)
        .where(GradeScale.id == scale_id, GradeScale.school_id == school_id)
    ).all()
    return [Band(r.grade, r.min_percent, r.max_percent) for r in rows]


def validate_bands(bands: list[tuple[str, Decimal, Decimal]]) -> list[str]:
    """Return problems: bands must not overlap and should cover 0..100."""
    errors: list[str] = []
    ordered = sorted(bands, key=lambda b: b[1])
    for (g1, _lo1, hi1), (g2, lo2, _hi2) in zip(ordered, ordered[1:], strict=False):
        if lo2 <= hi1:
            errors.append(f"Bands {g1} and {g2} overlap")
    if ordered and ordered[0][1] != 0:
        errors.append("Lowest band must start at 0")
    if ordered and ordered[-1][2] != 100:
        errors.append("Highest band must end at 100")
    if len({b[0] for b in bands}) != len(bands):
        errors.append("Grades must be unique")
    return errors
