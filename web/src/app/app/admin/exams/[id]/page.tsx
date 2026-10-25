"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { getClasses, getExamSubjects, getSubjects, type ExamSubject } from "@/lib/queries";
import { num } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/input";
import { Alert, Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

type Row = { max_marks: string; pass_marks: string; exam_date: string };

export default function ExamSubjectsPage() {
  const { id } = useParams<{ id: string }>();
  const exam = useQuery(() => unwrap(api.GET("/api/v1/exams/{exam_id}", { params: { path: { exam_id: id } } })), [id]);
  const subjects = useQuery(() => getExamSubjects(id), [id]);
  const classes = useQuery(getClasses, []);
  const allSubjects = useQuery(getSubjects, []);
  const [edits, setEdits] = React.useState<Record<string, Row>>({});
  const { busy, error, run } = useAction();

  const byClass = React.useMemo(() => {
    const groups = new Map<string, ExamSubject[]>();
    for (const es of subjects.data ?? []) {
      groups.set(es.class_name, [...(groups.get(es.class_name) ?? []), es]);
    }
    return [...groups.entries()];
  }, [subjects.data]);

  function rowValue(es: ExamSubject): Row {
    return (
      edits[es.id] ?? {
        max_marks: num(es.max_marks),
        pass_marks: es.pass_marks === null ? "" : num(es.pass_marks),
        exam_date: es.exam_date ?? "",
      }
    );
  }

  async function saveAll() {
    const items = (subjects.data ?? [])
      .filter((es) => edits[es.id])
      .map((es) => {
        const r = edits[es.id];
        return {
          class_id: es.class_id,
          subject_id: es.subject_id,
          max_marks: r.max_marks,
          pass_marks: r.pass_marks === "" ? null : r.pass_marks,
          exam_date: r.exam_date || null,
        };
      });
    if (!items.length) return;
    const ok = await run(() =>
      unwrap(api.PUT("/api/v1/exams/{exam_id}/subjects", { params: { path: { exam_id: id } }, body: { items } })),
    );
    if (ok) {
      setEdits({});
      subjects.reload();
    }
  }

  async function addOne(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const ok = await run(() =>
      unwrap(
        api.PUT("/api/v1/exams/{exam_id}/subjects", {
          params: { path: { exam_id: id } },
          body: {
            items: [
              {
                class_id: String(f.get("class_id")),
                subject_id: String(f.get("subject_id")),
                max_marks: String(f.get("max_marks")),
                pass_marks: (f.get("pass_marks") as string) || null,
              },
            ],
          },
        }),
      ),
    );
    if (ok) subjects.reload();
  }

  async function autoAdd(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const max = String(new FormData(e.currentTarget).get("max_marks"));
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/exams/{exam_id}/subjects/auto", { params: { path: { exam_id: id } }, body: { max_marks: max } }),
      ),
    );
    if (ok) subjects.reload();
  }

  async function remove(esId: string) {
    if (!confirm(t("common.confirmDelete"))) return;
    await run(() =>
      unwrap(
        api.DELETE("/api/v1/exams/{exam_id}/subjects/{exam_subject_id}", {
          params: { path: { exam_id: id, exam_subject_id: esId } },
        }),
      ),
    );
    subjects.reload();
  }

  return (
    <>
      <PageHeader title={exam.data?.name ?? ""} description={t("admin.examSubjects")} />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("admin.autoSubjects")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={autoAdd} className="flex items-end gap-3">
              <Field label={t("admin.maxMarks")} hint={t("admin.autoSubjectsHint")}>
                <Input name="max_marks" type="number" min={1} step="0.5" required defaultValue={100} className="w-32" />
              </Field>
              <Button type="submit" disabled={busy}>
                {t("admin.autoSubjects")}
              </Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("common.add")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={addOne} className="flex flex-wrap gap-2">
              <Select name="class_id" required className="w-28" aria-label={t("admin.class")}>
                <option value="">{t("admin.class")}</option>
                {(classes.data ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
              <Select name="subject_id" required className="w-40" aria-label={t("admin.subject")}>
                <option value="">{t("admin.subject")}</option>
                {(allSubjects.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
              <Input name="max_marks" required type="number" min={1} step="0.5" placeholder={t("admin.maxMarks")} className="w-28" />
              <Input name="pass_marks" type="number" min={0} step="0.5" placeholder={t("admin.passMarks")} className="w-28" />
              <Button type="submit" disabled={busy}>
                {t("common.add")}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {subjects.loading ? (
        <Spinner />
      ) : !byClass.length ? (
        <Empty>{t("common.none")}</Empty>
      ) : (
        <div className="flex flex-col gap-4">
          {byClass.map(([className, rows]) => (
            <Card key={className}>
              <CardHeader>
                <CardTitle>
                  {t("admin.class")} {className}
                </CardTitle>
              </CardHeader>
              <Table>
                <THead>
                  <TR>
                    <TH>{t("admin.subject")}</TH>
                    <TH>{t("admin.maxMarks")}</TH>
                    <TH>{t("admin.passMarks")}</TH>
                    <TH>{t("admin.examDate")}</TH>
                    <TH />
                  </TR>
                </THead>
                <TBody>
                  {rows.map((es) => {
                    const v = rowValue(es);
                    const set = (patch: Partial<Row>) => setEdits((e) => ({ ...e, [es.id]: { ...v, ...patch } }));
                    return (
                      <TR key={es.id}>
                        <TD className="font-medium">{es.subject_name}</TD>
                        <TD>
                          <Input
                            type="number"
                            min={1}
                            step="0.5"
                            value={v.max_marks}
                            onChange={(e) => set({ max_marks: e.target.value })}
                            className="h-9 w-24"
                            aria-label={t("admin.maxMarks")}
                          />
                        </TD>
                        <TD>
                          <Input
                            type="number"
                            min={0}
                            step="0.5"
                            value={v.pass_marks}
                            placeholder={t("admin.passDefault", { value: num(es.effective_pass_marks) })}
                            onChange={(e) => set({ pass_marks: e.target.value })}
                            className="h-9 w-36"
                            aria-label={t("admin.passMarks")}
                          />
                        </TD>
                        <TD>
                          <Input
                            type="date"
                            value={v.exam_date}
                            onChange={(e) => set({ exam_date: e.target.value })}
                            className="h-9 w-40"
                            aria-label={t("admin.examDate")}
                          />
                        </TD>
                        <TD className="text-right">
                          <Button size="icon" variant="ghost" aria-label={t("common.delete")} onClick={() => remove(es.id)}>
                            <Trash2 />
                          </Button>
                        </TD>
                      </TR>
                    );
                  })}
                </TBody>
              </Table>
            </Card>
          ))}
          <div>
            <Button onClick={saveAll} disabled={busy || !Object.keys(edits).length}>
              {t("common.save")}
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
