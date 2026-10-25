"use client";

import * as React from "react";
import { BookOpen, Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { currentYear, getAllTeachers, getClasses, getSections, getSubjects, getYears } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Alert, Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

function SubjectsEditor({ sectionId, onDone }: { sectionId: string; onDone: () => void }) {
  const all = useQuery(getSubjects, []);
  const current = useQuery(
    () => unwrap(api.GET("/api/v1/sections/{section_id}/subjects", { params: { path: { section_id: sectionId } } })),
    [sectionId],
  );
  const [chosen, setChosen] = React.useState<Set<string> | null>(null);
  const { busy, error, run } = useAction();
  const selected = chosen ?? new Set((current.data ?? []).map((s) => s.id));

  async function save() {
    const ok = await run(() =>
      unwrap(
        api.PUT("/api/v1/sections/{section_id}/subjects", {
          params: { path: { section_id: sectionId } },
          body: { subject_ids: [...selected] },
        }),
      ),
    );
    if (ok) onDone();
  }

  if (all.loading || current.loading) return <Spinner />;
  return (
    <div className="flex flex-col gap-3">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <div className="flex flex-wrap gap-3">
        {(all.data ?? []).map((s) => (
          <label key={s.id} className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm">
            <input
              type="checkbox"
              checked={selected.has(s.id)}
              onChange={(e) => {
                const next = new Set(selected);
                if (e.target.checked) next.add(s.id);
                else next.delete(s.id);
                setChosen(next);
              }}
            />
            {s.name}
          </label>
        ))}
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={save} disabled={busy}>
          {t("common.save")}
        </Button>
        <Button size="sm" variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}

export default function SectionsPage() {
  const years = useQuery(getYears, []);
  const [yearId, setYearId] = React.useState<string>("");
  const effectiveYear = yearId || currentYear(years.data)?.id || "";
  const sections = useQuery(() => getSections(effectiveYear), [effectiveYear], Boolean(effectiveYear));
  const classes = useQuery(getClasses, []);
  const teachers = useQuery(getAllTeachers, []);
  const [editingSubjects, setEditingSubjects] = React.useState<string | null>(null);
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/sections", {
          body: {
            academic_year_id: effectiveYear,
            class_id: String(f.get("class_id")),
            name: String(f.get("name")).trim().toUpperCase(),
            class_teacher_id: (f.get("class_teacher_id") as string) || null,
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      sections.reload();
    }
  }

  async function setClassTeacher(sectionId: string, teacherId: string) {
    await run(() =>
      unwrap(
        api.PATCH("/api/v1/sections/{section_id}", {
          params: { path: { section_id: sectionId } },
          body: { class_teacher_id: teacherId || null },
        }),
      ),
    );
    sections.reload();
  }

  async function remove(sectionId: string) {
    if (!confirm(t("common.confirmDelete"))) return;
    await run(() => unwrap(api.DELETE("/api/v1/sections/{section_id}", { params: { path: { section_id: sectionId } } })));
    sections.reload();
  }

  return (
    <>
      <PageHeader
        title={t("admin.sectionsTitle")}
        description={t("admin.sectionsBody")}
        actions={
          <Select value={effectiveYear} onChange={(e) => setYearId(e.target.value)} className="w-40">
            {(years.data ?? []).map((y) => (
              <option key={y.id} value={y.id}>
                {y.name}
              </option>
            ))}
          </Select>
        }
      />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <Card className="mb-4">
        <CardContent className="p-4">
          <form onSubmit={create} className="flex flex-wrap items-center gap-3">
            <Select name="class_id" required aria-label={t("admin.class")} className="w-40">
              <option value="">{t("admin.class")}</option>
              {(classes.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
            <Input name="name" required placeholder={t("admin.sectionName")} className="w-36" maxLength={10} />
            <Select name="class_teacher_id" aria-label={t("admin.classTeacher")} className="w-56">
              <option value="">{t("admin.classTeacher")}</option>
              {(teachers.data ?? []).map((tc) => (
                <option key={tc.id} value={tc.id}>
                  {tc.full_name}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={busy || !effectiveYear}>
              {t("common.add")}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        {sections.loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : !sections.data?.length ? (
          <div className="p-4">
            <Empty>{t("common.none")}</Empty>
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t("admin.section")}</TH>
                <TH>{t("admin.classTeacher")}</TH>
                <TH>{t("admin.studentsCount")}</TH>
                <TH className="text-right">{t("common.actions")}</TH>
              </TR>
            </THead>
            <TBody>
              {sections.data.map((s) => (
                <React.Fragment key={s.id}>
                  <TR>
                    <TD className="font-medium">{s.display_name}</TD>
                    <TD>
                      <Select
                        value={s.class_teacher_id ?? ""}
                        onChange={(e) => setClassTeacher(s.id, e.target.value)}
                        className="h-9 w-56"
                        aria-label={t("admin.classTeacher")}
                      >
                        <option value="">{t("common.none")}</option>
                        {(teachers.data ?? []).map((tc) => (
                          <option key={tc.id} value={tc.id}>
                            {tc.full_name}
                          </option>
                        ))}
                      </Select>
                    </TD>
                    <TD>{s.student_count}</TD>
                    <TD className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="outline" onClick={() => setEditingSubjects(s.id)}>
                          <BookOpen /> {t("admin.editSubjects")}
                        </Button>
                        <Button size="icon" variant="ghost" aria-label={t("common.delete")} onClick={() => remove(s.id)}>
                          <Trash2 />
                        </Button>
                      </div>
                    </TD>
                  </TR>
                  {editingSubjects === s.id ? (
                    <TR>
                      <TD colSpan={4} className="bg-muted/40">
                        <div className="mb-2 text-sm font-medium">{t("admin.sectionSubjects")}</div>
                        <SubjectsEditor sectionId={s.id} onDone={() => setEditingSubjects(null)} />
                      </TD>
                    </TR>
                  ) : null}
                </React.Fragment>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </>
  );
}
