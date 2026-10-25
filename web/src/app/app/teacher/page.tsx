"use client";

import Link from "next/link";
import { Users } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge, Empty, PageHeader, Spinner } from "@/components/ui/misc";

export default function TeacherHome() {
  const q = useQuery(() => unwrap(api.GET("/api/v1/teacher/my-assignments")), []);
  return (
    <>
      <PageHeader title={t("teacher.title")} description={t("teacher.body")} />
      {q.loading ? (
        <Spinner />
      ) : !q.data?.length ? (
        <Empty>{t("teacher.noAssignments")}</Empty>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {q.data.map((a) => (
            <Card key={`${a.section_id}-${a.subject_id}`}>
              <CardContent className="flex flex-col gap-3 p-5">
                <div>
                  <div className="text-lg font-semibold">{a.section_name}</div>
                  <div className="text-muted-foreground">{a.subject_name}</div>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Users className="h-4 w-4" aria-hidden /> {t("teacher.students", { n: a.student_count })}
                  {a.is_class_teacher ? <Badge tone="info">{t("teacher.classTeacher")}</Badge> : null}
                </div>
                <Button asChild>
                  <Link
                    href={`/app/teacher/marks?section=${a.section_id}&subject=${a.subject_id}&class=${a.class_id}&year=${a.academic_year_id}`}
                  >
                    {t("teacher.enterMarks")}
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
