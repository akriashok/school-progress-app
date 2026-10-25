"use client";

import * as React from "react";
import Link from "next/link";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { useAction, useQuery } from "@/lib/hooks";
import { currentYear, getSections, getYears } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Alert, Badge, Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Pager } from "@/components/pager";

const PAGE_SIZE = 50;

export default function StudentsPage() {
  const me = useMe();
  const canEdit = me.role === "SCHOOL_ADMIN";
  const years = useQuery(getYears, []);
  const year = currentYear(years.data);
  const sections = useQuery(() => getSections(year?.id), [year?.id], Boolean(year));
  const [sectionId, setSectionId] = React.useState("");
  const [q, setQ] = React.useState("");
  const [page, setPage] = React.useState(1);
  const list = useQuery(
    () =>
      unwrap(
        api.GET("/api/v1/students", {
          params: { query: { section_id: sectionId || undefined, q: q || undefined, page, page_size: PAGE_SIZE } },
        }),
      ),
    [sectionId, q, page],
  );
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/students", {
          body: {
            admission_no: String(f.get("admission_no")).trim(),
            full_name: String(f.get("full_name")).trim(),
            section_id: String(f.get("section_id")),
            roll_no: (f.get("roll_no") as string) || null,
            gender: ((f.get("gender") as string) || null) as "MALE" | "FEMALE" | "OTHER" | null,
            date_of_birth: (f.get("date_of_birth") as string) || null,
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      list.reload();
    }
  }

  const sectionOptions = (sections.data ?? []).map((s) => (
    <option key={s.id} value={s.id}>
      {s.display_name}
    </option>
  ));

  return (
    <>
      <PageHeader
        title={t("admin.studentsTitle")}
        actions={
          <>
            <Select
              value={sectionId}
              onChange={(e) => {
                setSectionId(e.target.value);
                setPage(1);
              }}
              className="w-44"
              aria-label={t("admin.filterSection")}
            >
              <option value="">
                {t("admin.filterSection")}: {t("common.all")}
              </option>
              {sectionOptions}
            </Select>
            <Input
              type="search"
              placeholder={t("common.search")}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              className="w-56"
            />
          </>
        }
      />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      {canEdit ? (
        <Card className="mb-4">
          <CardContent className="p-4">
            <form onSubmit={create} className="flex flex-wrap gap-3">
              <Input name="admission_no" required placeholder={t("admin.admissionNo")} className="w-36" />
              <Input name="full_name" required placeholder={t("common.name")} className="w-56" />
              <Select name="section_id" required className="w-40" aria-label={t("admin.section")}>
                <option value="">{t("admin.section")}</option>
                {sectionOptions}
              </Select>
              <Input name="roll_no" placeholder={t("admin.rollNo")} className="w-24" />
              <Select name="gender" className="w-32" aria-label={t("admin.gender")}>
                <option value="">{t("admin.gender")}</option>
                <option value="MALE">{t("admin.genderMALE")}</option>
                <option value="FEMALE">{t("admin.genderFEMALE")}</option>
                <option value="OTHER">{t("admin.genderOTHER")}</option>
              </Select>
              <Input name="date_of_birth" type="date" aria-label={t("admin.dob")} className="w-40" />
              <Button type="submit" disabled={busy}>
                {t("common.add")}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}
      <Card>
        {list.loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : !list.data?.items.length ? (
          <div className="p-4">
            <Empty>{t("common.none")}</Empty>
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <TR>
                  <TH>{t("admin.admissionNo")}</TH>
                  <TH>{t("common.name")}</TH>
                  <TH>{t("admin.section")}</TH>
                  <TH>{t("admin.rollNo")}</TH>
                  <TH>{t("admin.hasPin")}</TH>
                  <TH className="text-right">{t("common.actions")}</TH>
                </TR>
              </THead>
              <TBody>
                {list.data.items.map((s) => (
                  <TR key={s.id}>
                    <TD className="tabular-nums">{s.admission_no}</TD>
                    <TD className="font-medium">{s.full_name}</TD>
                    <TD>{s.section_name ?? "–"}</TD>
                    <TD>{s.roll_no ?? "–"}</TD>
                    <TD>
                      {s.has_pin ? (
                        <Badge tone="success">{t("admin.pinSet")}</Badge>
                      ) : (
                        <Badge>{t("admin.pinNotSet")}</Badge>
                      )}
                    </TD>
                    <TD className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/app/students/${s.id}`}>{t("nav.results")}</Link>
                        </Button>
                        {canEdit ? (
                          <Button asChild size="sm" variant="outline">
                            <Link href={`/app/admin/students/${s.id}`}>{t("common.edit")}</Link>
                          </Button>
                        ) : null}
                      </div>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
            <Pager page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
