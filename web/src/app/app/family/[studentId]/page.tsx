"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/misc";
import { StudentResultsView } from "@/components/student-results";

export default function ChildResultsPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const me = useMe();
  const isParent = me.role === "PARENT";
  const children = useQuery(() => unwrap(api.GET("/api/v1/children")), [isParent], isParent);
  const child = children.data?.find((c) => c.student_id === studentId);
  const title = isParent ? (child?.full_name ?? "") : me.full_name;

  return (
    <>
      <PageHeader
        title={title}
        description={child?.section_name ?? undefined}
        actions={
          isParent && (children.data?.length ?? 0) > 1 ? (
            <Button asChild variant="ghost">
              <Link href="/app/family">
                <ArrowLeft /> {t("nav.children")}
              </Link>
            </Button>
          ) : null
        }
      />
      <StudentResultsView studentId={studentId} examHref={(examId) => `/app/family/${studentId}/exams/${examId}`} />
    </>
  );
}
