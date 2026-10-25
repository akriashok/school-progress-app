"use client";

import * as React from "react";
import { t, type MessageKey } from "@/i18n";
import { api, unwrap, uploadFile } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { num } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export default function SchoolProfilePage() {
  const school = useQuery(() => unwrap(api.GET("/api/v1/school")), []);
  const staff = useQuery(() => unwrap(api.GET("/api/v1/staff")), []);
  const audit = useQuery(() => unwrap(api.GET("/api/v1/audit-logs", { params: { query: { limit: 30 } } })), []);
  const profile = useAction();
  const staffAction = useAction();
  const [saved, setSaved] = React.useState(false);
  const [logoVersion, setLogoVersion] = React.useState(0);

  if (school.loading) return <Spinner />;
  const s = school.data;
  if (!s) return <Alert tone="danger">{t("common.error")}</Alert>;

  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaved(false);
    const f = new FormData(e.currentTarget);
    const text = (k: string) => ((f.get(k) as string) || null);
    const ok = await profile.run(() =>
      unwrap(
        api.PATCH("/api/v1/school", {
          body: {
            name: String(f.get("name")),
            board: text("board"),
            address: text("address"),
            city: text("city"),
            state: text("state"),
            pincode: text("pincode"),
            phone: text("phone"),
            email: text("email"),
            show_rank: f.get("show_rank") === "on",
            pass_percent: String(f.get("pass_percent")),
          },
        }),
      ),
    );
    if (ok) {
      setSaved(true);
      school.reload();
    }
  }

  async function onLogo(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const ok = await profile.run(() => uploadFile("/api/v1/school/logo", file));
    if (ok) setLogoVersion((v) => v + 1);
  }

  async function addStaff(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await staffAction.run(() =>
      unwrap(
        api.POST("/api/v1/staff", {
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
      staff.reload();
    }
  }

  async function removeStaff(roleId: string) {
    if (!confirm(t("common.confirmDelete"))) return;
    await staffAction.run(() => unwrap(api.DELETE("/api/v1/staff/{role_id}", { params: { path: { role_id: roleId } } })));
    staff.reload();
  }

  return (
    <>
      <PageHeader title={t("admin.schoolTitle")} description={`${t("common.code")}: ${s.code}`} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="p-5">
            <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
              {profile.error ? <Alert tone="danger" className="sm:col-span-2">{profile.error}</Alert> : null}
              {saved ? <Alert tone="success" className="sm:col-span-2">{t("common.saved")}</Alert> : null}
              <Field label={t("common.name")} className="sm:col-span-2">
                <Input name="name" required defaultValue={s.name} />
              </Field>
              <Field label={t("admin.board")}>
                <Input name="board" defaultValue={s.board ?? ""} />
              </Field>
              <Field label={t("common.phone")}>
                <Input name="phone" defaultValue={s.phone ?? ""} />
              </Field>
              <Field label={t("admin.address")} className="sm:col-span-2">
                <Textarea name="address" defaultValue={s.address ?? ""} />
              </Field>
              <Field label={t("admin.city")}>
                <Input name="city" defaultValue={s.city ?? ""} />
              </Field>
              <Field label={t("admin.state")}>
                <Input name="state" defaultValue={s.state ?? ""} />
              </Field>
              <Field label={t("admin.pincode")}>
                <Input name="pincode" defaultValue={s.pincode ?? ""} />
              </Field>
              <Field label={t("common.email")}>
                <Input name="email" type="email" defaultValue={s.email ?? ""} />
              </Field>
              <Field label={t("admin.passPercent")}>
                <Input name="pass_percent" type="number" min={0} max={100} step="0.5" defaultValue={num(s.pass_percent)} />
              </Field>
              <label className="flex items-center gap-2 self-end pb-2 text-sm">
                <input type="checkbox" name="show_rank" defaultChecked={s.show_rank} className="h-4 w-4" />
                {t("admin.showRank")}
              </label>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={profile.busy}>
                  {t("common.save")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("admin.logo")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-start gap-3">
            {s.logo_url || logoVersion ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`/api/v1/public/schools/${s.code}/logo?v=${logoVersion}`}
                alt=""
                className="h-24 w-24 rounded-md border border-border object-contain"
              />
            ) : null}
            <Input type="file" accept="image/png,image/jpeg" onChange={onLogo} aria-label={t("admin.uploadLogo")} />
            <p className="text-xs text-muted-foreground">{t("admin.uploadLogo")}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>{t("admin.staffTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {staffAction.error ? <Alert tone="danger">{staffAction.error}</Alert> : null}
          <form onSubmit={addStaff} className="flex flex-wrap gap-3">
            <Input name="full_name" required placeholder={t("common.name")} className="w-52" />
            <Input name="phone" required inputMode="tel" placeholder={t("common.phone")} className="w-44" />
            <Select name="role" className="w-44" aria-label={t("profile.role")}>
              <option value="PRINCIPAL">{t("roles.PRINCIPAL")}</option>
              <option value="SCHOOL_ADMIN">{t("roles.SCHOOL_ADMIN")}</option>
            </Select>
            <Button type="submit" disabled={staffAction.busy}>
              {t("admin.addStaff")}
            </Button>
          </form>
          <Table>
            <THead>
              <TR>
                <TH>{t("common.name")}</TH>
                <TH>{t("common.phone")}</TH>
                <TH>{t("profile.role")}</TH>
                <TH>{t("common.status")}</TH>
                <TH />
              </TR>
            </THead>
            <TBody>
              {(staff.data ?? []).map((st) => (
                <TR key={st.role_id}>
                  <TD className="font-medium">{st.full_name}</TD>
                  <TD>{st.phone ?? "–"}</TD>
                  <TD>{t(`roles.${st.role}`)}</TD>
                  <TD>{st.is_active ? <Badge tone="success">{t("platform.active")}</Badge> : <Badge>{t("platform.inactive")}</Badge>}</TD>
                  <TD className="text-right">
                    {st.is_active ? (
                      <Button size="sm" variant="ghost" onClick={() => removeStaff(st.role_id)}>
                        {t("admin.remove")}
                      </Button>
                    ) : null}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>{t("admin.auditTitle")}</CardTitle>
        </CardHeader>
        <Table>
          <THead>
            <TR>
              <TH>{t("common.status")}</TH>
              <TH>{t("profile.role")}</TH>
              <TH>{t("admin.startDate")}</TH>
            </TR>
          </THead>
          <TBody>
            {(audit.data ?? []).map((a) => (
              <TR key={a.id}>
                <TD className="font-mono text-xs">{a.action}</TD>
                <TD>{a.role ? t(`roles.${a.role}` as MessageKey) : "–"}</TD>
                <TD className="text-sm text-muted-foreground">{new Date(a.created_at).toLocaleString("en-IN")}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>
    </>
  );
}
