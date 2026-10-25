"use client";

import * as React from "react";
import { t } from "@/i18n";
import { api, unwrap, type Schemas } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

function AdminsPanel({ school }: { school: Schemas["SchoolOut"] }) {
  const admins = useQuery(
    () => unwrap(api.GET("/api/v1/admin/schools/{school_id}/admins", { params: { path: { school_id: school.id } } })),
    [school.id],
  );
  const { busy, error, run } = useAction();
  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/admin/schools/{school_id}/admins", {
          params: { path: { school_id: school.id } },
          body: {
            full_name: String(f.get("full_name")),
            phone: String(f.get("phone")),
            role: String(f.get("role")) as "SCHOOL_ADMIN" | "PRINCIPAL",
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      admins.reload();
    }
  }
  return (
    <div className="flex flex-col gap-3 bg-muted/40 p-4">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <ul className="text-sm">
        {(admins.data ?? []).map((a) => (
          <li key={a.role_id}>
            {a.full_name} · {a.phone} · {t(`roles.${a.role}`)} {a.is_active ? "" : `(${t("platform.inactive")})`}
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap gap-2">
        <Input name="full_name" required placeholder={t("common.name")} className="w-48" />
        <Input name="phone" required placeholder={t("common.phone")} className="w-40" />
        <Select name="role" className="w-40" aria-label={t("profile.role")}>
          <option value="SCHOOL_ADMIN">{t("roles.SCHOOL_ADMIN")}</option>
          <option value="PRINCIPAL">{t("roles.PRINCIPAL")}</option>
        </Select>
        <Button type="submit" size="sm" disabled={busy}>
          {t("platform.addAdmin")}
        </Button>
      </form>
    </div>
  );
}

export default function PlatformPage() {
  const schools = useQuery(() => unwrap(api.GET("/api/v1/admin/schools")), []);
  const [open, setOpen] = React.useState<string | null>(null);
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/admin/schools", {
          body: {
            code: String(f.get("code")),
            name: String(f.get("name")),
            city: (f.get("city") as string) || null,
            board: (f.get("board") as string) || null,
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      schools.reload();
    }
  }

  async function toggle(s: Schemas["SchoolOut"]) {
    await run(() =>
      unwrap(
        api.PATCH("/api/v1/admin/schools/{school_id}", {
          params: { path: { school_id: s.id } },
          body: { is_active: !s.is_active },
        }),
      ),
    );
    schools.reload();
  }

  return (
    <>
      <PageHeader title={t("platform.title")} />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>{t("platform.createSchool")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={create} className="flex flex-wrap gap-3">
            <Input name="code" required pattern="[A-Za-z0-9]{3,12}" placeholder={t("platform.schoolCode")} className="w-72" />
            <Input name="name" required placeholder={t("platform.schoolName")} className="w-64" />
            <Input name="city" placeholder={t("admin.city")} className="w-40" />
            <Input name="board" placeholder={t("admin.board")} className="w-32" />
            <Button type="submit" disabled={busy}>
              {t("common.create")}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        {schools.loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t("common.code")}</TH>
                <TH>{t("common.name")}</TH>
                <TH>{t("admin.city")}</TH>
                <TH>{t("common.status")}</TH>
                <TH />
              </TR>
            </THead>
            <TBody>
              {(schools.data ?? []).map((s) => (
                <React.Fragment key={s.id}>
                  <TR>
                    <TD className="font-mono">{s.code}</TD>
                    <TD className="font-medium">{s.name}</TD>
                    <TD>{s.city ?? "–"}</TD>
                    <TD>{s.is_active ? <Badge tone="success">{t("platform.active")}</Badge> : <Badge>{t("platform.inactive")}</Badge>}</TD>
                    <TD className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline" onClick={() => setOpen(open === s.id ? null : s.id)}>
                          {t("platform.admins")}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => toggle(s)}>
                          {s.is_active ? t("platform.deactivate") : t("platform.activate")}
                        </Button>
                      </div>
                    </TD>
                  </TR>
                  {open === s.id ? (
                    <TR>
                      <TD colSpan={5} className="p-0">
                        <AdminsPanel school={s} />
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
