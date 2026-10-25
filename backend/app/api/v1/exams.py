import uuid

from fastapi import APIRouter, BackgroundTasks

from app.core.deps import AdminCtx, ManagerCtx, StaffCtx, TeacherCtx
from app.schemas.common import Ok
from app.schemas.exams import (
    AutoExamSubjectsIn,
    BulkMarksIn,
    BulkMarksOut,
    ExamIn,
    ExamOut,
    ExamStatus,
    ExamSubjectOut,
    ExamSubjectsIn,
    ExamUpdate,
    MarksGrid,
    MyAssignment,
    PublicationIn,
    PublicationOut,
    SubmissionOut,
    SubmitMarksIn,
)
from app.services import exams as svc
from app.services import marks, notifications

router = APIRouter(tags=["exams"])


@router.get("/exams", response_model=list[ExamOut])
def list_exams(ctx: StaffCtx, academic_year_id: uuid.UUID | None = None) -> list[ExamOut]:
    return [ExamOut.model_validate(e) for e in svc.list_exams(ctx, academic_year_id)]


@router.post("/exams", response_model=ExamOut, status_code=201)
def create_exam(body: ExamIn, ctx: AdminCtx) -> ExamOut:
    return ExamOut.model_validate(svc.create_exam(ctx, body))


@router.get("/exams/{exam_id}", response_model=ExamOut)
def get_exam(exam_id: uuid.UUID, ctx: StaffCtx) -> ExamOut:
    return ExamOut.model_validate(svc.get_exam(ctx, exam_id))


@router.patch("/exams/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: uuid.UUID, body: ExamUpdate, ctx: AdminCtx) -> ExamOut:
    return ExamOut.model_validate(svc.update_exam(ctx, exam_id, body))


@router.delete("/exams/{exam_id}", response_model=Ok)
def delete_exam(exam_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_exam(ctx, exam_id)
    return Ok()


@router.get("/exams/{exam_id}/subjects", response_model=list[ExamSubjectOut])
def list_exam_subjects(exam_id: uuid.UUID, ctx: StaffCtx) -> list[ExamSubjectOut]:
    svc.get_exam(ctx, exam_id)
    return svc.exam_subject_rows(ctx, exam_id)


@router.put(
    "/exams/{exam_id}/subjects",
    response_model=list[ExamSubjectOut],
    summary="Create or update max/pass marks per class + subject",
)
def put_exam_subjects(exam_id: uuid.UUID, body: ExamSubjectsIn, ctx: AdminCtx) -> list[ExamSubjectOut]:
    return svc.upsert_exam_subjects(ctx, exam_id, body.items)


@router.post(
    "/exams/{exam_id}/subjects/auto",
    response_model=list[ExamSubjectOut],
    summary="Add every subject each class studies, with the same max marks",
)
def auto_exam_subjects(exam_id: uuid.UUID, body: AutoExamSubjectsIn, ctx: AdminCtx) -> list[ExamSubjectOut]:
    return svc.auto_exam_subjects(ctx, exam_id, body)


@router.delete("/exams/{exam_id}/subjects/{exam_subject_id}", response_model=Ok)
def delete_exam_subject(exam_id: uuid.UUID, exam_subject_id: uuid.UUID, ctx: AdminCtx) -> Ok:
    svc.delete_exam_subject(ctx, exam_id, exam_subject_id)
    return Ok()


@router.get("/exams/{exam_id}/status", response_model=ExamStatus, summary="Marks entry status per section x subject")
def exam_status(exam_id: uuid.UUID, ctx: ManagerCtx) -> ExamStatus:
    return svc.exam_status(ctx, exam_id)


@router.get("/exams/{exam_id}/publications", response_model=list[PublicationOut])
def list_publications(exam_id: uuid.UUID, ctx: ManagerCtx) -> list[PublicationOut]:
    return marks.list_publications(ctx, exam_id)


@router.post(
    "/exams/{exam_id}/publications",
    response_model=list[PublicationOut],
    summary="Publish results (whole exam or chosen sections); notifies parents/students",
)
def publish(exam_id: uuid.UUID, body: PublicationIn, ctx: ManagerCtx, tasks: BackgroundTasks) -> list[PublicationOut]:
    newly = marks.publish(ctx, exam_id, body.section_ids)
    tasks.add_task(notifications.notify_results_published, ctx.school_id, exam_id, newly)
    return marks.list_publications(ctx, exam_id)


@router.delete("/exams/{exam_id}/publications", response_model=list[PublicationOut], summary="Unpublish")
def unpublish(exam_id: uuid.UUID, body: PublicationIn, ctx: ManagerCtx) -> list[PublicationOut]:
    marks.unpublish(ctx, exam_id, body.section_ids)
    return marks.list_publications(ctx, exam_id)


# ------------------------------------------------------------------- marks
@router.get("/teacher/my-assignments", response_model=list[MyAssignment], tags=["marks"])
def my_assignments(ctx: TeacherCtx, academic_year_id: uuid.UUID | None = None) -> list[MyAssignment]:
    return marks.my_assignments(ctx, academic_year_id)


@router.get("/marks", response_model=MarksGrid, tags=["marks"])
def get_marks(exam_subject_id: uuid.UUID, section_id: uuid.UUID, ctx: StaffCtx) -> MarksGrid:
    return marks.get_grid(ctx, exam_subject_id, section_id)


@router.put("/marks/bulk", response_model=BulkMarksOut, tags=["marks"])
def put_marks(body: BulkMarksIn, ctx: StaffCtx) -> BulkMarksOut:
    return marks.bulk_put(ctx, body)


@router.post("/marks/submit", response_model=SubmissionOut, tags=["marks"])
def submit_marks(body: SubmitMarksIn, ctx: StaffCtx) -> SubmissionOut:
    return marks.submit(ctx, body.exam_subject_id, body.section_id)
