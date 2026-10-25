"use client";

import Link from "next/link";
import { CheckCircle2, Circle } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useQuery } from "@/lib/hooks";
import { currentYear, getExams, getSections, getYears } from "@/lib/queries";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader, Spinner } from "@/components/ui/misc";

export default function AdminOverview() {
  const q = useQuery(async () => {
    const years = await getYears();
    const year = currentYear(years);
    const [sections, exams, students, teachers] = await Promise.all([
      year ? getSections(year.id) : Promise.resolve([]),
      year ? getExams(year.id) : Promise.resolve([]),
      unwrap(api.GET("/api/v1/students", { params: { query: { page: 1, page_size: 1 } } })),
      unwrap(api.GET("/api/v1/teachers", { params: { query: { page: 1, page_size: 1 } } })),
    ]);
    return { years, sections, exams, students: students.total, teachers: teachers.total };
  }, []);

  const d = q.data;
  const steps = d
    ? [
        { done: d.years.some((y) => y.is_current), label: t("admin.step1"), href: "/app/admin/years",
          meta: t("admin.countYears", { n: d.years.length }) },
        { done: d.sections.length > 0, label: t("admin.step2"), href: "/app/admin/sections",
          meta: t("admin.countSections", { n: d.sections.length }) },
        { done: d.students > 0, label: t("admin.step3"), href: "/app/admin/imports",
          meta: t("admin.countStudents", { n: d.students }) },
        { done: d.teachers > 0, label: t("admin.step4"), href: "/app/admin/assignments",
          meta: t("admin.countTeachers", { n: d.teachers }) },
        { done: d.exams.length > 0, label: t("admin.step5"), href: "/app/admin/exams",
          meta: t("admin.countExams", { n: d.exams.length }) },
      ]
    : [];

  return (
    <>
      <PageHeader title={t("admin.overviewTitle")} description={t("admin.overviewBody")} />
      {q.loading ? (
        <Spinner />
      ) : (
        <ol className="flex flex-col gap-3">
          {steps.map((s, i) => (
            <li key={s.href}>
              <Link href={s.href}>
                <Card className="transition-colors hover:border-primary">
                  <CardContent className="flex items-center gap-4 p-4">
                    {s.done ? (
                      <CheckCircle2 className="h-6 w-6 shrink-0 text-success" aria-hidden />
                    ) : (
                      <Circle className="h-6 w-6 shrink-0 text-muted-foreground" aria-hidden />
                    )}
                    <div className="flex-1">
                      <div className="font-medium">
                        {i + 1}. {s.label}
                      </div>
                      <div className="text-sm text-muted-foreground">{s.meta}</div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
