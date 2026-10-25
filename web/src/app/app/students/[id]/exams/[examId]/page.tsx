"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { t } from "@/i18n";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/misc";
import { ExamDetailView } from "@/components/student-results";

export default function StaffStudentExamPage() {
  const { id, examId } = useParams<{ id: string; examId: string }>();
  return (
    <>
      <PageHeader
        title={t("family.examDetail")}
        actions={
          <Button asChild variant="ghost">
            <Link href={`/app/students/${id}`}>
              <ArrowLeft /> {t("common.back")}
            </Link>
          </Button>
        }
      />
      <ExamDetailView studentId={id} examId={examId} />
    </>
  );
}
