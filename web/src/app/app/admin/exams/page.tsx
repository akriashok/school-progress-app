"use client";

import * as React from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { currentYear, getExams, getYears } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Alert, Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export default function ExamsAdminPage() {
  const years = useQuery(getYears, []);
  const [yearId, setYearId] = React.useState("");
  const effectiveYear = yearId || currentYear(years.data)?.id || "";
  const exams = useQuery(() => getExams(effectiveYear), [effectiveYear], Boolean(effectiveYear));
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/exams", {
          body: {
            academic_year_id: effectiveYear,
            name: String(f.get("name")),
            sequence: Number(f.get("sequence")),
            start_date: (f.get("start_date") as string) || null,
            end_date: (f.get("end_date") as string) || null,
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      exams.reload();
    }
  }

  async function remove(id: string) {
    if (!confirm(t("common.confirmDelete"))) return;
    await run(() => unwrap(api.DELETE("/api/v1/exams/{exam_id}", { params: { path: { exam_id: id } } })));
    exams.reload();
  }

  return (
    <>
      <PageHeader
        title={t("admin.examsTitle")}
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
          <form onSubmit={create} className="flex flex-wrap gap-3">
            <Input name="name" required placeholder={t("admin.examName")} className="w-52" />
            <Input
              name="sequence"
              required
              type="number"
              min={1}
              max={50}
              placeholder={t("admin.sequence")}
              defaultValue={(exams.data?.length ?? 0) + 1}
              className="w-32"
              aria-label={t("admin.sequence")}
            />
            <Input name="start_date" type="date" aria-label={t("admin.startDate")} className="w-40" />
            <Input name="end_date" type="date" aria-label={t("admin.endDate")} className="w-40" />
            <Button type="submit" disabled={busy || !effectiveYear}>
              {t("common.add")}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        {exams.loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : !exams.data?.length ? (
          <div className="p-4">
            <Empty>{t("common.none")}</Empty>
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t("admin.sequence")}</TH>
                <TH>{t("admin.examName")}</TH>
                <TH>{t("admin.startDate")}</TH>
                <TH className="text-right">{t("common.actions")}</TH>
              </TR>
            </THead>
            <TBody>
              {exams.data.map((ex) => (
                <TR key={ex.id}>
                  <TD className="tabular-nums">{ex.sequence}</TD>
                  <TD className="font-medium">{ex.name}</TD>
                  <TD>{ex.start_date ?? "–"}</TD>
                  <TD className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/app/admin/exams/${ex.id}`}>{t("admin.examSubjects")}</Link>
                      </Button>
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/app/principal/exams/${ex.id}`}>{t("principal.publishStatus")}</Link>
                      </Button>
                      <Button size="icon" variant="ghost" aria-label={t("common.delete")} onClick={() => remove(ex.id)}>
                        <Trash2 />
                      </Button>
                    </div>
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
