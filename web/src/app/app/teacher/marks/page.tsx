"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { t } from "@/i18n";
import { useQuery } from "@/lib/hooks";
import { getExamSubjects, getExams } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Field, Select } from "@/components/ui/input";
import { Alert, PageHeader, Spinner } from "@/components/ui/misc";
import { MarksGrid } from "@/components/marks-grid";

function MarksEntry() {
  const params = useSearchParams();
  const sectionId = params.get("section") ?? "";
  const subjectId = params.get("subject") ?? "";
  const classId = params.get("class") ?? "";
  const yearId = params.get("year") ?? undefined;
  const exams = useQuery(() => getExams(yearId), [yearId]);
  const [examId, setExamId] = React.useState("");
  // Default: the latest exam that has started (future exams usually have no marks yet).
  const today = new Date().toISOString().slice(0, 10);
  const started = (exams.data ?? []).filter((ex) => !ex.start_date || ex.start_date <= today);
  const chosenExam = examId || started.at(-1)?.id || exams.data?.[0]?.id || "";
  const subjects = useQuery(() => getExamSubjects(chosenExam), [chosenExam], Boolean(chosenExam));
  const examSubject = subjects.data?.find((es) => es.class_id === classId && es.subject_id === subjectId);

  return (
    <>
      <PageHeader
        title={t("marks.title")}
        actions={
          <Button asChild variant="ghost">
            <Link href="/app/teacher">
              <ArrowLeft /> {t("common.back")}
            </Link>
          </Button>
        }
      />
      {exams.loading ? (
        <Spinner />
      ) : (
        <div className="flex flex-col gap-4">
          <Field label={t("marks.exam")} className="max-w-xs">
            <Select value={chosenExam} onChange={(e) => setExamId(e.target.value)}>
              {(exams.data ?? []).map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.name}
                </option>
              ))}
            </Select>
          </Field>
          {subjects.loading ? (
            <Spinner />
          ) : examSubject ? (
            <MarksGrid key={examSubject.id} examSubjectId={examSubject.id} sectionId={sectionId} />
          ) : chosenExam ? (
            <Alert tone="warning">{t("marks.noExamSubject")}</Alert>
          ) : null}
        </div>
      )}
    </>
  );
}

export default function TeacherMarksPage() {
  return (
    <React.Suspense fallback={<Spinner />}>
      <MarksEntry />
    </React.Suspense>
  );
}
