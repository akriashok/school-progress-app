"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Download } from "lucide-react";
import { t } from "@/i18n";
import { api, downloadFile, unwrap } from "@/lib/api";
import { errorMessage, useAction, useQuery } from "@/lib/hooks";
import { currentYear, getExams, getYears } from "@/lib/queries";
import { asNumber, pct } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Alert, Badge, Empty, PageHeader, Spinner, Stat } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { MagnitudeBars } from "@/components/charts";

function ExportButton({ report, examId, label }: { report: string; examId: string; label?: string }) {
  const { busy, run } = useAction();
  return (
    <Button
      size="sm"
      variant="outline"
      disabled={busy}
      onClick={() => run(() => downloadFile(`/api/v1/dashboard/export?report=${report}&exam_id=${examId}`, `${report}.xlsx`).then(() => true))}
    >
      <Download /> {label ?? t("common.export")}
    </Button>
  );
}

function Dashboard({ examId }: { examId: string }) {
  const router = useRouter();
  const q = useQuery(async () => {
    const opts = { params: { query: { exam_id: examId } } };
    const [summary, sections, subjects, attention, toppers] = await Promise.all([
      unwrap(api.GET("/api/v1/dashboard/summary", opts)),
      unwrap(api.GET("/api/v1/dashboard/sections", opts)),
      unwrap(api.GET("/api/v1/dashboard/subjects", opts)),
      unwrap(api.GET("/api/v1/dashboard/attention", opts)),
      unwrap(api.GET("/api/v1/dashboard/toppers", opts)),
    ]);
    return { summary, sections, subjects, attention, toppers };
  }, [examId]);

  if (q.loading) return <Spinner />;
  if (q.error || !q.data) return <Alert tone="danger">{errorMessage(q.error)}</Alert>;
  const { summary, sections, subjects, attention, toppers } = q.data;
  if (!summary.students_with_results) return <Empty>{t("principal.noData")}</Empty>;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={t("principal.students")} value={summary.students_with_results} hint={`/ ${summary.students}`} />
        <Stat label={t("principal.average")} value={pct(summary.average_percent)} />
        <Stat label={t("principal.passRate")} value={pct(summary.pass_percent)} />
        <Stat label={t("principal.published")} value={`${summary.sections_published} / ${summary.sections_total}`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between">
            <CardTitle>{t("principal.sectionComparison")}</CardTitle>
            <ExportButton report="sections" examId={examId} />
          </CardHeader>
          <CardContent>
            <MagnitudeBars
              valueLabel={t("principal.average")}
              data={sections.map((s) => ({ id: s.section_id, label: s.section_name.replace("Class ", ""), value: asNumber(s.average_percent) }))}
              onSelect={(id) => router.push(`/app/principal/sections/${id}?exam=${examId}`)}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex-row items-start justify-between">
            <CardTitle>{t("principal.gradeDistribution")}</CardTitle>
            <ExportButton report="summary" examId={examId} />
          </CardHeader>
          <CardContent>
            <MagnitudeBars
              percent={false}
              valueLabel={t("principal.students")}
              data={summary.grade_distribution.map((g) => ({ label: g.grade, value: g.count }))}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("admin.sectionsTitle")}</CardTitle>
        </CardHeader>
        <Table>
          <THead>
            <TR>
              <TH>{t("admin.section")}</TH>
              <TH className="text-right">{t("principal.students")}</TH>
              <TH className="text-right">{t("principal.average")}</TH>
              <TH className="text-right">{t("principal.passRate")}</TH>
              <TH>{t("principal.publishStatus")}</TH>
              <TH />
            </TR>
          </THead>
          <TBody>
            {sections.map((s) => (
              <TR key={s.section_id}>
                <TD className="font-medium">{s.section_name}</TD>
                <TD className="text-right tabular-nums">{s.students}</TD>
                <TD className="text-right tabular-nums">{pct(s.average_percent)}</TD>
                <TD className="text-right tabular-nums">{pct(s.pass_percent)}</TD>
                <TD>{s.published ? <Badge tone="success">{t("marks.published")}</Badge> : <Badge>{t("marks.draft")}</Badge>}</TD>
                <TD className="text-right">
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/app/principal/sections/${s.section_id}?exam=${examId}`}>{t("common.view")}</Link>
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between">
            <CardTitle>{t("principal.subjectPerformance")}</CardTitle>
            <ExportButton report="subjects" examId={examId} />
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
              {subjects.map((s, i) => (
                <TR key={s.subject_id}>
                  <TD className="font-medium">
                    {s.subject_name}
                    {i === 0 && subjects.length > 1 ? <Badge tone="warning" className="ml-2">↓</Badge> : null}
                  </TD>
                  <TD className="text-right tabular-nums">{pct(s.average_percent)}</TD>
                  <TD className="text-right tabular-nums">{pct(s.pass_percent)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
        <Card>
          <CardHeader className="flex-row items-start justify-between">
            <CardTitle>{t("principal.toppers")}</CardTitle>
            <ExportButton report="toppers" examId={examId} />
          </CardHeader>
          <Table>
            <THead>
              <TR>
                <TH>{t("admin.section")}</TH>
                <TH>{t("principal.rank")}</TH>
                <TH>{t("principal.student")}</TH>
                <TH className="text-right">%</TH>
              </TR>
            </THead>
            <TBody>
              {toppers.map((tp) => (
                <TR key={`${tp.section_id}-${tp.student_id}`}>
                  <TD>{tp.section_name}</TD>
                  <TD className="tabular-nums">{tp.rank}</TD>
                  <TD className="font-medium">
                    <Link href={`/app/students/${tp.student_id}`} className="hover:underline">
                      {tp.full_name}
                    </Link>
                  </TD>
                  <TD className="text-right tabular-nums">{pct(tp.percentage)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-start justify-between">
          <div>
            <CardTitle>
              {t("principal.attention")} ({attention.length})
            </CardTitle>
            <CardDescription>{t("principal.attentionHint")}</CardDescription>
          </div>
          <ExportButton report="attention" examId={examId} />
        </CardHeader>
        {attention.length === 0 ? (
          <CardContent>
            <Empty>{t("principal.noAttention")}</Empty>
          </CardContent>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t("principal.student")}</TH>
                <TH>{t("admin.section")}</TH>
                <TH className="text-right">%</TH>
                <TH className="text-right">{t("principal.previous")}</TH>
                <TH>{t("principal.reasons")}</TH>
              </TR>
            </THead>
            <TBody>
              {attention.map((a) => (
                <TR key={a.student_id}>
                  <TD className="font-medium">
                    <Link href={`/app/students/${a.student_id}`} className="hover:underline">
                      {a.full_name}
                    </Link>
                    <div className="text-xs text-muted-foreground">{a.admission_no}</div>
                  </TD>
                  <TD>{a.section_name}</TD>
                  <TD className="text-right tabular-nums">{pct(a.percentage)}</TD>
                  <TD className="text-right tabular-nums">{pct(a.previous_percentage)}</TD>
                  <TD className="text-sm">{a.reasons.join(" · ")}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}

export default function PrincipalDashboard() {
  const years = useQuery(getYears, []);
  const year = currentYear(years.data);
  const exams = useQuery(() => getExams(year?.id), [year?.id], Boolean(year));
  const [examId, setExamId] = React.useState("");

  // Default to the latest exam that has any marks.
  const latest = useQuery(
    async () => {
      for (const ex of [...(exams.data ?? [])].reverse()) {
        const s = await unwrap(api.GET("/api/v1/dashboard/summary", { params: { query: { exam_id: ex.id } } }));
        if (s.students_with_results) return ex.id;
      }
      return exams.data?.[0]?.id ?? "";
    },
    [exams.data],
    Boolean(exams.data),
  );
  const chosen = examId || latest.data || "";

  return (
    <>
      <PageHeader
        title={t("principal.dashboardTitle")}
        description={year?.name}
        actions={
          <Select value={chosen} onChange={(e) => setExamId(e.target.value)} className="w-48" aria-label={t("principal.exam")}>
            {(exams.data ?? []).map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name}
              </option>
            ))}
          </Select>
        }
      />
      {years.loading || exams.loading || latest.loading ? (
        <Spinner />
      ) : chosen ? (
        <Dashboard examId={chosen} />
      ) : (
        <Empty>{t("principal.noData")}</Empty>
      )}
    </>
  );
}
