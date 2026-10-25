"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2, AlertTriangle, FileDown } from "lucide-react";
import { t, type MessageKey } from "@/i18n";
import { api, downloadFile, unwrap, type Schemas } from "@/lib/api";
import { errorMessage, useAction, useQuery } from "@/lib/hooks";
import { asNumber, num, pct } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Alert, Badge, Empty, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ProgressLines } from "@/components/charts";

type Summary = Schemas["ExamResultSummary"];

function PassBadge({ passed }: { passed: boolean }) {
  return passed ? (
    <Badge tone="success" className="gap-1">
      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> {t("family.passed")}
    </Badge>
  ) : (
    <Badge tone="warning" className="gap-1">
      <AlertTriangle className="h-3.5 w-3.5" aria-hidden /> {t("family.needsImprovement")}
    </Badge>
  );
}

function ReportCardButton({ studentId, examId }: { studentId: string; examId: string }) {
  const { busy, error, run } = useAction();
  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        variant="outline"
        disabled={busy}
        onClick={() =>
          run(() => downloadFile(`/api/v1/students/${studentId}/report-cards/${examId}.pdf`, "report-card.pdf").then(() => true))
        }
      >
        <FileDown /> {t("family.reportCard")}
      </Button>
      {error ? <span className="text-sm text-destructive">{error}</span> : null}
    </div>
  );
}

function LatestCard({ r, studentId, examHref }: { r: Summary; studentId: string; examHref: string }) {
  return (
    <Card>
      <CardHeader>
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{t("family.latest")}</div>
        <CardTitle className="text-xl">{r.exam_name}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-6">
          <div>
            <div className="text-4xl font-bold tabular-nums">{pct(r.percentage)}</div>
            <div className="text-sm text-muted-foreground">
              {num(r.total_obtained)} / {num(r.total_max)}
            </div>
          </div>
          <div>
            <div className="text-3xl font-semibold">{r.grade ?? "–"}</div>
            <div className="text-sm text-muted-foreground">{t("family.grade")}</div>
          </div>
          {r.rank !== null && r.rank !== undefined ? (
            <div className="text-sm text-muted-foreground">{t("family.rank", { rank: r.rank, size: r.section_size })}</div>
          ) : null}
          <PassBadge passed={r.passed} />
        </div>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href={examHref}>{t("family.bySubject")}</Link>
          </Button>
          <ReportCardButton studentId={studentId} examId={r.exam_id} />
        </div>
      </CardContent>
    </Card>
  );
}

export function StudentResultsView({ studentId, examHref }: { studentId: string; examHref: (examId: string) => string }) {
  const results = useQuery(
    () => unwrap(api.GET("/api/v1/students/{student_id}/results", { params: { path: { student_id: studentId } } })),
    [studentId],
  );
  const progress = useQuery(
    () => unwrap(api.GET("/api/v1/students/{student_id}/progress", { params: { path: { student_id: studentId } } })),
    [studentId],
  );
  const [subjectId, setSubjectId] = React.useState("");

  if (results.loading || progress.loading) return <Spinner />;
  if (results.error) return <Alert tone="danger">{errorMessage(results.error)}</Alert>;
  const rows = results.data ?? [];
  if (!rows.length) return <Empty>{t("family.noResults")}</Empty>;

  const p = progress.data;
  const subject = p?.subjects.find((s) => s.subject_id === subjectId);
  const chartData = (p?.overall ?? []).map((pt) => {
    const sp = subject?.points.find((x) => x.exam_id === pt.exam_id);
    return { label: pt.exam_name, overall: asNumber(pt.percentage), subject: sp ? asNumber(sp.percentage) : null };
  });
  const series = [{ key: "overall", name: t("family.overall") }];
  if (subject) series.push({ key: "subject", name: subject.subject_name });

  return (
    <div className="flex flex-col gap-4">
      <LatestCard r={rows[0]} studentId={studentId} examHref={examHref(rows[0].exam_id)} />

      {p && p.overall.length ? (
        <Card>
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
            <CardTitle>{t("family.progress")}</CardTitle>
            <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} className="h-9 w-48" aria-label={t("family.subject")}>
              <option value="">{t("family.overall")}</option>
              {p.subjects.map((s) => (
                <option key={s.subject_id} value={s.subject_id}>
                  {s.subject_name}
                </option>
              ))}
            </Select>
          </CardHeader>
          <CardContent>
            <ProgressLines data={chartData} series={series} />
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("family.allExams")}</CardTitle>
        </CardHeader>
        <Table>
          <THead>
            <TR>
              <TH>{t("principal.exam")}</TH>
              <TH>{t("family.total")}</TH>
              <TH>{t("family.percentage")}</TH>
              <TH>{t("family.grade")}</TH>
              <TH>{t("principal.rank")}</TH>
              <TH />
            </TR>
          </THead>
          <TBody>
            {rows.map((r) => (
              <TR key={r.exam_id}>
                <TD className="font-medium">
                  {r.exam_name} {!r.published ? <Badge className="ml-1">{t("marks.draft")}</Badge> : null}
                </TD>
                <TD className="tabular-nums">
                  {num(r.total_obtained)} / {num(r.total_max)}
                </TD>
                <TD className="tabular-nums">{pct(r.percentage)}</TD>
                <TD>{r.grade ?? "–"}</TD>
                <TD className="tabular-nums">{r.rank ?? "–"}</TD>
                <TD className="text-right">
                  <Button asChild size="sm" variant="outline">
                    <Link href={examHref(r.exam_id)}>{t("common.view")}</Link>
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>
    </div>
  );
}

const statusKey: Record<string, MessageKey> = { ABSENT: "marks.absent", EXEMPT: "marks.exempt" };

export function ExamDetailView({ studentId, examId }: { studentId: string; examId: string }) {
  const q = useQuery(
    () =>
      unwrap(
        api.GET("/api/v1/students/{student_id}/results/{exam_id}", {
          params: { path: { student_id: studentId, exam_id: examId } },
        }),
      ),
    [studentId, examId],
  );
  if (q.loading) return <Spinner />;
  if (q.error || !q.data) return <Alert tone="danger">{errorMessage(q.error)}</Alert>;
  const d = q.data;
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-6 p-5">
          <div>
            <div className="text-sm text-muted-foreground">{d.student_name}</div>
            <div className="text-xl font-semibold">{d.exam_name}</div>
          </div>
          <div className="text-3xl font-bold tabular-nums">{pct(d.percentage)}</div>
          <div className="text-2xl font-semibold">{d.grade ?? "–"}</div>
          {d.rank !== null && d.rank !== undefined ? (
            <div className="text-sm text-muted-foreground">{t("family.rank", { rank: d.rank, size: d.section_size })}</div>
          ) : null}
          <PassBadge passed={d.passed} />
          <div className="ml-auto">
            <ReportCardButton studentId={studentId} examId={examId} />
          </div>
        </CardContent>
      </Card>
      <Card>
        <Table>
          <THead>
            <TR>
              <TH>{t("family.subject")}</TH>
              <TH className="text-right">{t("family.marks")}</TH>
              <TH className="text-right">{t("family.outOf")}</TH>
              <TH className="text-right">%</TH>
              <TH>{t("family.grade")}</TH>
            </TR>
          </THead>
          <TBody>
            {d.subjects.map((s) => (
              <TR key={s.subject_id}>
                <TD className="font-medium">{s.subject_name}</TD>
                <TD className={`text-right tabular-nums ${s.passed === false ? "font-semibold text-destructive" : ""}`}>
                  {statusKey[s.status] ? t(statusKey[s.status]) : num(s.marks)}
                </TD>
                <TD className="text-right tabular-nums text-muted-foreground">{num(s.max_marks)}</TD>
                <TD className="text-right tabular-nums">{pct(s.percentage)}</TD>
                <TD>{s.grade ?? "–"}</TD>
              </TR>
            ))}
            <TR className="font-semibold">
              <TD>{t("family.total")}</TD>
              <TD className="text-right tabular-nums">{num(d.total_obtained)}</TD>
              <TD className="text-right tabular-nums">{num(d.total_max)}</TD>
              <TD className="text-right tabular-nums">{pct(d.percentage)}</TD>
              <TD>{d.grade ?? "–"}</TD>
            </TR>
          </TBody>
        </Table>
      </Card>
    </div>
  );
}
