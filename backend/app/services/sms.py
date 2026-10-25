"""OTP SMS delivery. Only transactional OTP SMS in v1 (no promotional SMS)."""

import logging

import httpx

from app.core.config import get_settings
from app.core.security import mask_phone

log = logging.getLogger("app.sms")


def send_otp(phone: str, code: str) -> None:
    s = get_settings()
    if s.sms_backend == "console":
        # Dev only (config refuses this outside local/test). Phone is masked.
        log.warning("DEV OTP for %s: %s", mask_phone(phone), code)
        return
    if not s.sms_http_url or not s.sms_http_api_key:
        log.error("sms_not_configured")
        return
    try:
        httpx.post(
            s.sms_http_url,
            headers={"Authorization": f"Bearer {s.sms_http_api_key}"},
            json={"to": phone, "otp": code},
            timeout=10,
        ).raise_for_status()
    except httpx.HTTPError as exc:
        log.error("otp_send_failed type=%s", type(exc).__name__)
