"use client";

import * as React from "react";
import { Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { currentYear, getAllTeachers, getSections, getSubjects, getYears } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { Alert, Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export default function AssignmentsPage() {
  const years = useQuery(getYears, []);
  const year = currentYear(years.data);
  const sections = useQuery(() => getSections(year?.id), [year?.id], Boolean(year));
  const subjects = useQuery(getSubjects, []);
  const teachers = useQuery(getAllTeachers, []);
  const [filterTeacher, setFilterTeacher] = React.useState("");
  const [filterSection, setFilterSection] = React.useState("");
  const list = useQuery(
    () =>
      unwrap(
        api.GET("/api/v1/teacher-assignments", {
          params: {
            query: {
              academic_year_id: year?.id,
              teacher_id: filterTeacher || undefined,
              section_id: filterSection || undefined,
            },
          },
        }),
      ),
    [year?.id, filterTeacher, filterSection],
    Boolean(year),
  );
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/teacher-assignments", {
          body: {
            teacher_id: String(f.get("teacher_id")),
            section_id: String(f.get("section_id")),
            subject_id: String(f.get("subject_id")),
          },
        }),
      ),
    );
    if (ok) list.reload();
  }

  async function remove(id: string) {
    await run(() =>
      unwrap(api.DELETE("/api/v1/teacher-assignments/{assignment_id}", { params: { path: { assignment_id: id } } })),
    );
    list.reload();
  }

  const teacherOptions = (teachers.data ?? []).map((tc) => (
    <option key={tc.id} value={tc.id}>
      {tc.full_name}
    </option>
  ));
  const sectionOptions = (sections.data ?? []).map((s) => (
    <option key={s.id} value={s.id}>
      {s.display_name}
    </option>
  ));

  return (
    <>
      <PageHeader title={t("admin.assignmentsTitle")} description={t("admin.assignmentsBody")} />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <Card className="mb-4">
        <CardContent className="p-4">
          <form onSubmit={create} className="flex flex-wrap gap-3">
            <Select name="teacher_id" required className="w-56" aria-label={t("admin.teacher")}>
              <option value="">{t("admin.teacher")}</option>
              {teacherOptions}
            </Select>
            <Select name="section_id" required className="w-40" aria-label={t("admin.section")}>
              <option value="">{t("admin.section")}</option>
              {sectionOptions}
            </Select>
            <Select name="subject_id" required className="w-48" aria-label={t("admin.subject")}>
              <option value="">{t("admin.subject")}</option>
              {(subjects.data ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={busy}>
              {t("common.add")}
            </Button>
          </form>
        </CardContent>
      </Card>
      <div className="mb-3 flex flex-wrap gap-3">
        <Select value={filterTeacher} onChange={(e) => setFilterTeacher(e.target.value)} className="w-56">
          <option value="">
            {t("admin.teacher")}: {t("common.all")}
          </option>
          {teacherOptions}
        </Select>
        <Select value={filterSection} onChange={(e) => setFilterSection(e.target.value)} className="w-48">
          <option value="">
            {t("admin.section")}: {t("common.all")}
          </option>
          {sectionOptions}
        </Select>
      </div>
      <Card>
        {list.loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : !list.data?.length ? (
          <div className="p-4">
            <Empty>{t("common.none")}</Empty>
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t("admin.section")}</TH>
                <TH>{t("admin.subject")}</TH>
                <TH>{t("admin.teacher")}</TH>
                <TH className="text-right">{t("common.actions")}</TH>
              </TR>
            </THead>
            <TBody>
              {list.data.map((a) => (
                <TR key={a.id}>
                  <TD className="font-medium">{a.section_name}</TD>
                  <TD>{a.subject_name}</TD>
                  <TD>{a.teacher_name}</TD>
                  <TD className="text-right">
                    <Button size="icon" variant="ghost" aria-label={t("common.delete")} onClick={() => remove(a.id)}>
                      <Trash2 />
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </>
  );
}
