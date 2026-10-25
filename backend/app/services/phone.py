import re

_DIGITS = re.compile(r"\D")


class InvalidPhone(ValueError):
    pass


def normalize_phone(raw: str | int | None) -> str:
    """Normalise an Indian mobile number to E.164 (+91XXXXXXXXXX)."""
    if raw is None:
        raise InvalidPhone("phone is required")
    s = str(raw).strip()
    if s.endswith(".0"):  # Excel numeric cells
        s = s[:-2]
    digits = _DIGITS.sub("", s)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10:
        raise InvalidPhone("phone must be 10 digits")
    if digits[0] not in "6789":
        raise InvalidPhone("phone must be an Indian mobile number")
    return f"+91{digits}"
