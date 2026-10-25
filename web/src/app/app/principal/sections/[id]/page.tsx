"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Download } from "lucide-react";
import { t } from "@/i18n";
import { api, downloadFile, unwrap } from "@/lib/api";
import { errorMessage, useAction, useQuery } from "@/lib/hooks";
import { pct, num } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

function SectionView() {
  const { id } = useParams<{ id: string }>();
  const examId = useSearchParams().get("exam") ?? "";
  const router = useRouter();
  const { busy, run } = useAction();
  const q = useQuery(async () => {
    const [section, students, subjects, attention] = await Promise.all([
      unwrap(api.GET("/api/v1/sections/{section_id}", { params: { path: { section_id: id } } })),
      unwrap(api.GET("/api/v1/dashboard/students", { params: { query: { exam_id: examId, section_id: id } } })),
      unwrap(api.GET("/api/v1/dashboard/subjects", { params: { query: { exam_id: examId, section_id: id } } })),
      unwrap(api.GET("/api/v1/dashboard/attention", { params: { query: { exam_id: examId, section_id: id } } })),
    ]);
    return { section, students, subjects, attention: new Set(attention.map((a) => a.student_id)) };
  }, [id, examId]);

  if (q.loading) return <Spinner />;
  if (q.error || !q.data) return <Alert tone="danger">{errorMessage(q.error)}</Alert>;
  const { section, students, subjects, attention } = q.data;

  return (
    <>
      <PageHeader
        title={section.display_name}
        description={section.class_teacher_name ? `${t("admin.classTeacher")}: ${section.class_teacher_name}` : undefined}
        actions={
          <>
            <Button
              variant="outline"
              disabled={busy}
              onClick={() =>
                run(() =>
                  downloadFile(
                    `/api/v1/dashboard/export?report=students&exam_id=${examId}&section_id=${id}`,
                    `${section.display_name}.xlsx`.replace(/\s+/g, "_"),
                  ).then(() => true),
                )
              }
            >
              <Download /> {t("common.export")}
            </Button>
            <Button variant="ghost" onClick={() => router.back()}>
              <ArrowLeft /> {t("common.back")}
            </Button>
          </>
        }
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t("principal.sectionView")}</CardTitle>
          </CardHeader>
          <Table>
            <THead>
              <TR>
                <TH>{t("principal.rank")}</TH>
                <TH>{t("principal.student")}</TH>
                <TH className="text-right">{t("principal.total")}</TH>
                <TH className="text-right">%</TH>
                <TH>{t("principal.grade")}</TH>
              </TR>
            </THead>
            <TBody>
              {students.map((s) => (
                <TR key={s.student_id}>
                  <TD className="tabular-nums">{s.rank ?? "–"}</TD>
                  <TD className="font-medium">
                    <Link href={`/app/students/${s.student_id}`} className="hover:underline">
                      {s.full_name}
                    </Link>
                    {attention.has(s.student_id) ? (
                      <Badge tone="warning" className="ml-2">
                        {t("principal.attention")}
                      </Badge>
                    ) : null}
                    <div className="text-xs text-muted-foreground">{s.admission_no}</div>
                  </TD>
                  <TD className="text-right tabular-nums">
                    {s.total_obtained === null ? "–" : `${num(s.total_obtained)} / ${num(s.total_max)}`}
                  </TD>
                  <TD className="text-right tabular-nums">{pct(s.percentage)}</TD>
                  <TD>{s.grade ?? "–"}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("principal.subjectPerformance")}</CardTitle>
          </CardHeader>
          <Table>
            <THead>
              <TR>
                <TH>{t("admin.subject")}</TH>
                <TH className="text-right">{t("principal.average")}</TH>
                <TH className="text-right">{t("principal.passRate")}</TH>
              </TR>
            </THead>
            <TBody>
              {subjects.map((s) => (
                <TR key={s.subject_id}>
                  <TD>{s.subject_name}</TD>
                  <TD className="text-right tabular-nums">{pct(s.average_percent)}</TD>
                  <TD className="text-right tabular-nums">{pct(s.pass_percent)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
      </div>
    </>
  );
}

export default function SectionPage() {
  return (
    <React.Suspense fallback={<Spinner />}>
      <SectionView />
    </React.Suspense>
  );
}
