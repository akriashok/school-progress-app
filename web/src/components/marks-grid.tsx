"use client";

import * as React from "react";
import { Download } from "lucide-react";
import { t } from "@/i18n";
import { api, ApiError, downloadFile, unwrap, type Schemas } from "@/lib/api";
import { errorMessage, useAction, useQuery } from "@/lib/hooks";
import { cn, num } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Alert, Badge, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ImportPanel } from "@/components/import-panel";

type Grid = Schemas["MarksGrid"];
type Status = "PRESENT" | "ABSENT" | "EXEMPT";

function display(row: Grid["rows"][number]): string {
  if (row.status === "ABSENT") return "AB";
  if (row.status === "EXEMPT") return "EX";
  return row.marks === null ? "" : num(row.marks);
}

/** Parse a cell: number, AB, EX or blank. Returns an error string if invalid. */
function parseCell(text: string, max: number): { status: Status; marks: string | null } | null | string {
  const v = text.trim().toUpperCase();
  if (v === "") return null;
  if (v === "AB" || v === "A") return { status: "ABSENT", marks: null };
  if (v === "EX") return { status: "EXEMPT", marks: null };
  if (!/^\d+(\.\d{1,2})?$/.test(v)) return t("marks.invalidValue", { max: num(max) });
  const n = Number(v);
  if (n < 0 || n > max) return t("marks.invalidValue", { max: num(max) });
  return { status: "PRESENT", marks: v };
}

export function MarksGrid({ examSubjectId, sectionId }: { examSubjectId: string; sectionId: string }) {
  const grid = useQuery(
    () => unwrap(api.GET("/api/v1/marks", { params: { query: { exam_subject_id: examSubjectId, section_id: sectionId } } })),
    [examSubjectId, sectionId],
  );
  const [values, setValues] = React.useState<Record<string, string>>({});
  const [reason, setReason] = React.useState("");
  const [notice, setNotice] = React.useState<string | null>(null);
  const [rowErrors, setRowErrors] = React.useState<Record<string, string>>({});
  const { busy, error, setError, run } = useAction();
  const inputs = React.useRef<(HTMLInputElement | null)[]>([]);

  React.useEffect(() => {
    if (grid.data) {
      setValues(Object.fromEntries(grid.data.rows.map((r) => [r.student_id, display(r)])));
      setRowErrors({});
    }
  }, [grid.data]);

  if (grid.loading && !grid.data) return <Spinner />;
  if (grid.error) return <Alert tone="danger">{errorMessage(grid.error)}</Alert>;
  const g = grid.data;
  if (!g) return null;

  const max = Number(g.max_marks);
  const original = Object.fromEntries(g.rows.map((r) => [r.student_id, display(r)]));
  const changed = g.rows.filter((r) => (values[r.student_id] ?? "") !== original[r.student_id]);
  const localErrors: Record<string, string> = {};
  for (const r of g.rows) {
    const parsed = parseCell(values[r.student_id] ?? "", max);
    if (typeof parsed === "string") localErrors[r.student_id] = parsed;
  }
  const enteredCount = g.rows.filter((r) => (values[r.student_id] ?? "").trim() !== "").length;
  const allErrors = { ...rowErrors, ...localErrors };

  async function save(): Promise<boolean> {
    setNotice(null);
    if (Object.keys(localErrors).length) return false;
    const entries = changed
      .map((r) => {
        const parsed = parseCell(values[r.student_id] ?? "", max);
        if (parsed === null || typeof parsed === "string") return null;
        return { student_id: r.student_id, status: parsed.status, marks: parsed.marks };
      })
      .filter((e): e is NonNullable<typeof e> => e !== null);
    if (!entries.length) return true;
    try {
      const res = await unwrap(
        api.PUT("/api/v1/marks/bulk", {
          body: { exam_subject_id: examSubjectId, section_id: sectionId, entries, reason: reason || null },
        }),
      );
      setNotice(t("marks.savedSummary", { created: res.created, updated: res.updated }));
      setRowErrors({});
      grid.reload();
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.code === "MARKS_INVALID" && Array.isArray(e.details)) {
        const errs: Record<string, string> = {};
        for (const d of e.details as { student_id: string; message: string }[]) errs[d.student_id] = d.message;
        setRowErrors(errs);
      }
      setError(errorMessage(e));
      return false;
    }
  }

  async function submit() {
    const ok = await run(async () => {
      if (!(await save())) throw new Error("save failed");
      return unwrap(api.POST("/api/v1/marks/submit", { body: { exam_subject_id: examSubjectId, section_id: sectionId } }));
    });
    if (ok) {
      setNotice(t("marks.submittedOk"));
      grid.reload();
    }
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>, i: number) {
    if (e.key === "Enter" || e.key === "ArrowDown") {
      e.preventDefault();
      inputs.current[i + 1]?.focus();
      inputs.current[i + 1]?.select();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      inputs.current[i - 1]?.focus();
      inputs.current[i - 1]?.select();
    }
  }

  const statusBadge = g.published ? (
    <Badge tone="success">{t("marks.published")}</Badge>
  ) : g.submission_status === "SUBMITTED" ? (
    <Badge tone="info">{t("marks.submitted")}</Badge>
  ) : (
    <Badge>{t("marks.draft")}</Badge>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-lg font-semibold">
          {g.exam_name} · {g.subject_name} · {g.section_name}
        </div>
        {statusBadge}
        <span className="text-sm text-muted-foreground">
          {t("marks.max", { max: num(g.max_marks), pass: num(g.pass_marks) })}
        </span>
      </div>
      {!g.can_edit ? <Alert tone="warning">{t("marks.lockedPublished")}</Alert> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {g.reason_required ? (
        <Field label={t("marks.reason")}>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
        </Field>
      ) : null}

      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border p-3 text-sm text-muted-foreground">
            <span>{t("marks.hint")}</span>
            <span className="tabular-nums">{t("marks.entered", { n: enteredCount, total: g.rows.length })}</span>
          </div>
          <Table>
            <THead>
              <TR>
                <TH className="w-16">{t("admin.rollNo")}</TH>
                <TH className="w-32">{t("admin.admissionNo")}</TH>
                <TH>{t("marks.student")}</TH>
                <TH className="w-40">{t("marks.marks")}</TH>
              </TR>
            </THead>
            <TBody>
              {g.rows.map((r, i) => {
                const err = allErrors[r.student_id];
                const dirty = (values[r.student_id] ?? "") !== original[r.student_id];
                return (
                  <TR key={r.student_id}>
                    <TD className="tabular-nums text-muted-foreground">{r.roll_no ?? "–"}</TD>
                    <TD className="tabular-nums">{r.admission_no}</TD>
                    <TD className="font-medium">{r.full_name}</TD>
                    <TD>
                      <Input
                        ref={(el) => {
                          inputs.current[i] = el;
                        }}
                        value={values[r.student_id] ?? ""}
                        disabled={!g.can_edit}
                        inputMode="decimal"
                        autoComplete="off"
                        aria-label={`${t("marks.marks")} ${r.full_name}`}
                        aria-invalid={Boolean(err)}
                        onKeyDown={(e) => onKey(e, i)}
                        onFocus={(e) => e.currentTarget.select()}
                        onChange={(e) => setValues((v) => ({ ...v, [r.student_id]: e.target.value }))}
                        className={cn(
                          "h-9 w-28 text-right tabular-nums",
                          dirty && "border-primary bg-primary/5",
                          err && "border-destructive bg-destructive/5",
                        )}
                      />
                      {err ? <div className="mt-1 text-xs text-destructive">{err}</div> : null}
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
        </CardContent>
      </Card>

      {g.can_edit ? (
        <div className="sticky bottom-0 z-10 flex flex-wrap items-center gap-3 border-t border-border bg-background/95 py-3 backdrop-blur">
          <Button onClick={() => run(save)} disabled={busy || !changed.length || Boolean(Object.keys(localErrors).length)}>
            {t("marks.saveDraft")}
          </Button>
          {!g.published ? (
            <Button variant="secondary" onClick={submit} disabled={busy || Boolean(Object.keys(localErrors).length)}>
              {t("marks.submit")}
            </Button>
          ) : null}
          {changed.length ? (
            <span className="text-sm text-muted-foreground">{t("marks.unsaved", { n: changed.length })}</span>
          ) : null}
        </div>
      ) : null}

      {g.can_edit ? (
        <Card>
          <CardContent className="flex flex-col gap-4 p-5">
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="outline"
                onClick={() =>
                  downloadFile(
                    `/api/v1/imports/templates/marks?exam_subject_id=${examSubjectId}&section_id=${sectionId}`,
                    `marks_${g.section_name}_${g.subject_name}.xlsx`.replace(/\s+/g, "_"),
                  ).catch((e) => setError(errorMessage(e)))
                }
              >
                <Download /> {t("marks.downloadTemplate")}
              </Button>
            </div>
            <ImportPanel
              uploadPath={`/api/v1/imports/marks?exam_subject_id=${examSubjectId}&section_id=${sectionId}`}
              previewColumns={[
                { key: "admission_no", label: t("admin.admissionNo") },
                { key: "student_name", label: t("marks.student") },
                { key: "status", label: t("common.status") },
                { key: "marks", label: t("marks.marks") },
              ]}
              commitReason={reason || null}
              onCommitted={() => grid.reload()}
            />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
