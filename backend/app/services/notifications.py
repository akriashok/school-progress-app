"""Push notifications (FCM) and device registration. Only result-publish pushes in v1."""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal, set_tenant
from app.core.deps import CurrentUser
from app.core.errors import NotFound
from app.models import Device, Exam, Guardian, Student, StudentEnrolment, StudentGuardian

log = logging.getLogger("app.push")


class PushSender(Protocol):
    def send(self, tokens: list[str], title: str, body: str, data: dict[str, str]) -> int: ...


class LogSender:
    """Dev/test sender. Logs counts only, never tokens or names."""

    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def send(self, tokens: list[str], title: str, body: str, data: dict[str, str]) -> int:
        self.sent.append({"tokens": list(tokens), "title": title, "data": data})
        log.info("push_sent count=%d type=%s", len(tokens), data.get("type"))
        return len(tokens)


class FcmSender:
    """FCM HTTP v1 using a service account (google-auth)."""

    def __init__(self, project_id: str, service_account_file: str) -> None:
        from google.oauth2 import service_account

        self.project_id = project_id
        self.creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )

    def send(self, tokens: list[str], title: str, body: str, data: dict[str, str]) -> int:
        from google.auth.transport.requests import Request

        self.creds.refresh(Request())
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        ok = 0
        with httpx.Client(timeout=10) as client:
            for t in tokens:
                msg = {
                    "message": {
                        "token": t,
                        "notification": {"title": title, "body": body},
                        "data": data,
                        "android": {"priority": "high"},
                    }
                }
                r = client.post(url, headers={"Authorization": f"Bearer {self.creds.token}"}, content=json.dumps(msg))
                ok += r.status_code == 200
        log.info("push_sent count=%d ok=%d type=%s", len(tokens), ok, data.get("type"))
        return ok


_sender: PushSender | None = None


def get_sender() -> PushSender:
    global _sender
    if _sender is None:
        s = get_settings()
        if s.push_backend == "fcm" and s.fcm_project_id and s.fcm_service_account_file:
            _sender = FcmSender(s.fcm_project_id, s.fcm_service_account_file)
        else:
            _sender = LogSender()
    return _sender


def set_sender(sender: PushSender) -> None:
    global _sender
    _sender = sender


# -------------------------------------------------------------- devices
def register_device(db: Session, user: CurrentUser, token: str, platform: str) -> Device:
    device = db.scalar(select(Device).where(Device.fcm_token == token))
    if device is None:
        device = Device(user_id=user.user_id, fcm_token=token, platform=platform)
        db.add(device)
    else:
        device.user_id, device.platform, device.last_seen_at = user.user_id, platform, datetime.now(UTC)
    db.flush()
    return device


def delete_device(db: Session, user: CurrentUser, device_id: uuid.UUID) -> None:
    device = db.scalar(select(Device).where(Device.id == device_id, Device.user_id == user.user_id))
    if device is None:
        raise NotFound("Device")
    db.delete(device)


# ---------------------------------------------------------- publishing
def recipients_for_sections(
    db: Session, school_id: uuid.UUID, exam: Exam, section_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    student_ids = select(StudentEnrolment.student_id).where(
        StudentEnrolment.school_id == school_id,
        StudentEnrolment.section_id.in_(section_ids),
        StudentEnrolment.academic_year_id == exam.academic_year_id,
    )
    parents = db.scalars(
        select(Guardian.user_id)
        .join(StudentGuardian, StudentGuardian.guardian_id == Guardian.id)
        .where(
            StudentGuardian.student_id.in_(student_ids), Guardian.deleted_at.is_(None), Guardian.user_id.is_not(None)
        )
    ).all()
    students = db.scalars(
        select(Student.user_id).where(
            Student.id.in_(student_ids), Student.user_id.is_not(None), Student.deleted_at.is_(None)
        )
    ).all()
    return {u for u in [*parents, *students] if u is not None}


def notify_results_published(school_id: uuid.UUID, exam_id: uuid.UUID, section_ids: list[uuid.UUID]) -> None:
    """Background job: push 'results published' to parents and students of these sections."""
    if not section_ids:
        return
    db = SessionLocal()
    set_tenant(db, school_id)
    try:
        exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.school_id == school_id))
        if exam is None:
            return
        users = recipients_for_sections(db, school_id, exam, section_ids)
        if not users:
            return
        tokens = list(db.scalars(select(Device.fcm_token).where(Device.user_id.in_(users))))
        if tokens:
            get_sender().send(
                tokens,
                "Results published",
                f"{exam.name} results are now available.",
                {"type": "RESULTS_PUBLISHED", "exam_id": str(exam.id)},
            )
    finally:
        db.close()
