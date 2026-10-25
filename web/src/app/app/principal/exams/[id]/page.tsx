"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { t } from "@/i18n";
import { api, unwrap, type Schemas } from "@/lib/api";
import { errorMessage, useAction, useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, Badge, type Tone, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

type Row = Schemas["ExamStatusRow"];

const statusTone: Record<Row["status"], Tone> = { SUBMITTED: "success", DRAFT: "warning", NOT_STARTED: "default" };
const statusLabel = {
  SUBMITTED: "principal.submitted",
  DRAFT: "principal.draft",
  NOT_STARTED: "principal.notStarted",
} as const;

export default function ExamPublishPage() {
  const { id } = useParams<{ id: string }>();
  const exam = useQuery(() => unwrap(api.GET("/api/v1/exams/{exam_id}", { params: { path: { exam_id: id } } })), [id]);
  const status = useQuery(() => unwrap(api.GET("/api/v1/exams/{exam_id}/status", { params: { path: { exam_id: id } } })), [id]);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const { busy, error, run } = useAction();

  const bySection = React.useMemo(() => {
    const m = new Map<string, { name: string; published: boolean; rows: Row[] }>();
    for (const r of status.data?.rows ?? []) {
      const g = m.get(r.section_id) ?? { name: r.section_name, published: r.published, rows: [] };
      g.rows.push(r);
      m.set(r.section_id, g);
    }
    return [...m.entries()];
  }, [status.data]);

  async function publish(sectionIds: string[] | null) {
    if (!confirm(t("principal.publishConfirm"))) return;
    const ok = await run(() =>
      unwrap(api.POST("/api/v1/exams/{exam_id}/publications", { params: { path: { exam_id: id } }, body: { section_ids: sectionIds } })),
    );
    if (ok) {
      setSelected(new Set());
      status.reload();
    }
  }

  async function unpublish(sectionIds: string[]) {
    if (!confirm(t("principal.unpublishConfirm"))) return;
    const ok = await run(() =>
      unwrap(api.DELETE("/api/v1/exams/{exam_id}/publications", { params: { path: { exam_id: id } }, body: { section_ids: sectionIds } })),
    );
    if (ok) status.reload();
  }

  if (status.loading) return <Spinner />;
  if (status.error || !status.data) return <Alert tone="danger">{errorMessage(status.error)}</Alert>;
  const s = status.data;

  return (
    <>
      <PageHeader
        title={exam.data?.name ?? ""}
        description={t("principal.submittedCount", { done: s.submitted, total: s.total })}
        actions={
          <>
            <Button variant="outline" disabled={busy || selected.size === 0} onClick={() => publish([...selected])}>
              {t("principal.publishSelected")} ({selected.size})
            </Button>
            <Button disabled={busy} onClick={() => publish(null)}>
              {t("principal.publishAll")}
            </Button>
          </>
        }
      />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <div className="flex flex-col gap-4">
        {bySection.map(([sectionId, g]) => {
          const done = g.rows.filter((r) => r.status === "SUBMITTED").length;
          return (
            <Card key={sectionId}>
              <CardHeader className="flex-row flex-wrap items-center gap-3">
                {!g.published ? (
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    aria-label={g.name}
                    checked={selected.has(sectionId)}
                    onChange={(e) => {
                      const next = new Set(selected);
                      if (e.target.checked) next.add(sectionId);
                      else next.delete(sectionId);
                      setSelected(next);
                    }}
                  />
                ) : null}
                <CardTitle>{g.name}</CardTitle>
                {g.published ? <Badge tone="success">{t("marks.published")}</Badge> : <Badge>{t("marks.draft")}</Badge>}
                <span className="text-sm text-muted-foreground">
                  {t("principal.submittedCount", { done, total: g.rows.length })}
                </span>
                <div className="ml-auto flex gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/app/principal/sections/${sectionId}?exam=${id}`}>{t("principal.sectionView")}</Link>
                  </Button>
                  {g.published ? (
                    <Button size="sm" variant="outline" disabled={busy} onClick={() => unpublish([sectionId])}>
                      {t("principal.unpublish")}
                    </Button>
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <THead>
                    <TR>
                      <TH>{t("admin.subject")}</TH>
                      <TH>{t("principal.teachers")}</TH>
                      <TH className="text-right">{t("principal.entered")}</TH>
                      <TH>{t("common.status")}</TH>
                      <TH />
                    </TR>
                  </THead>
                  <TBody>
                    {g.rows.map((r) => (
                      <TR key={r.exam_subject_id}>
                        <TD className="font-medium">{r.subject_name}</TD>
                        <TD className="text-sm">{r.teachers.join(", ") || "–"}</TD>
                        <TD className="text-right tabular-nums">
                          {r.entered} / {r.students}
                        </TD>
                        <TD>
                          <Badge tone={statusTone[r.status]}>{t(statusLabel[r.status])}</Badge>
                        </TD>
                        <TD className="text-right">
                          <Button asChild size="sm" variant="ghost">
                            <Link href={`/app/principal/marks?es=${r.exam_subject_id}&section=${sectionId}`}>{t("common.open")}</Link>
                          </Button>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
