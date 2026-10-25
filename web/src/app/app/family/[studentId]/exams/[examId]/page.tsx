"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { t } from "@/i18n";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/misc";
import { ExamDetailView } from "@/components/student-results";

export default function ChildExamPage() {
  const { studentId, examId } = useParams<{ studentId: string; examId: string }>();
  return (
    <>
      <PageHeader
        title={t("family.examDetail")}
        actions={
          <Button asChild variant="ghost">
            <Link href={`/app/family/${studentId}`}>
              <ArrowLeft /> {t("common.back")}
            </Link>
          </Button>
        }
      />
      <ExamDetailView studentId={studentId} examId={examId} />
    </>
  );
}
