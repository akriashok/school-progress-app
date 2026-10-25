"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { t } from "@/i18n";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/misc";
import { StudentResultsView } from "@/components/student-results";

/** Staff view of one student's results (principal / admin / their teachers). */
export default function StaffStudentPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  return (
    <>
      <PageHeader
        title={t("principal.studentProfile")}
        actions={
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft /> {t("common.back")}
          </Button>
        }
      />
      <StudentResultsView studentId={id} examHref={(examId) => `/app/students/${id}/exams/${examId}`} />
    </>
  );
}
