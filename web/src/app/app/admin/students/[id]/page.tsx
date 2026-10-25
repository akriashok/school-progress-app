"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { t, type MessageKey } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { currentYear, getSections, getYears } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select } from "@/components/ui/input";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui/misc";

type Gender = "MALE" | "FEMALE" | "OTHER";
type Relation = "FATHER" | "MOTHER" | "GUARDIAN";

export default function StudentEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const student = useQuery(
    () => unwrap(api.GET("/api/v1/students/{student_id}", { params: { path: { student_id: id } } })),
    [id],
  );
  const years = useQuery(getYears, []);
  const year = currentYear(years.data);
  const sections = useQuery(() => getSections(year?.id), [year?.id], Boolean(year));
  const details = useAction();
  const guardians = useAction();
  const pin = useAction();
  const [pinSaved, setPinSaved] = React.useState(false);
  const [saved, setSaved] = React.useState(false);

  if (student.loading) return <Spinner />;
  if (!student.data) return <Alert tone="danger">{t("common.error")}</Alert>;
  const s = student.data;

  async function saveDetails(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaved(false);
    const f = new FormData(e.currentTarget);
    const ok = await details.run(() =>
      unwrap(
        api.PATCH("/api/v1/students/{student_id}", {
          params: { path: { student_id: id } },
          body: {
            full_name: String(f.get("full_name")),
            section_id: (f.get("section_id") as string) || null,
            roll_no: (f.get("roll_no") as string) || null,
            gender: ((f.get("gender") as string) || null) as Gender | null,
            date_of_birth: (f.get("date_of_birth") as string) || null,
          },
        }),
      ),
    );
    if (ok) {
      setSaved(true);
      student.reload();
    }
  }

  async function addGuardian(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await guardians.run(() =>
      unwrap(
        api.POST("/api/v1/students/{student_id}/guardians", {
          params: { path: { student_id: id } },
          body: {
            guardian: { full_name: String(f.get("full_name")), phone: String(f.get("phone")) },
            relation: String(f.get("relation")) as Relation,
            is_primary: f.get("is_primary") === "on",
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      student.reload();
    }
  }

  async function unlink(guardianId: string) {
    if (!confirm(t("common.confirmDelete"))) return;
    await guardians.run(() =>
      unwrap(
        api.DELETE("/api/v1/students/{student_id}/guardians/{guardian_id}", {
          params: { path: { student_id: id, guardian_id: guardianId } },
        }),
      ),
    );
    student.reload();
  }

  async function savePin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const value = String(new FormData(form).get("pin"));
    const ok = await pin.run(() =>
      unwrap(api.POST("/api/v1/students/{student_id}/pin", { params: { path: { student_id: id } }, body: { pin: value } })),
    );
    if (ok) {
      form.reset();
      setPinSaved(true);
      student.reload();
    }
  }

  async function remove() {
    if (!confirm(t("common.confirmDelete"))) return;
    const ok = await details.run(() =>
      unwrap(api.DELETE("/api/v1/students/{student_id}", { params: { path: { student_id: id } } })),
    );
    if (ok) router.replace("/app/admin/students");
  }

  return (
    <>
      <PageHeader
        title={s.full_name}
        description={`${t("admin.admissionNo")} ${s.admission_no}${s.section_name ? ` · ${s.section_name}` : ""}`}
        actions={
          <>
            <Button asChild variant="outline">
              <Link href={`/app/students/${s.id}`}>{t("nav.results")}</Link>
            </Button>
            <Button variant="destructive" onClick={remove}>
              {t("common.delete")}
            </Button>
          </>
        }
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("common.edit")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={saveDetails} className="grid gap-4 sm:grid-cols-2">
              {details.error ? <Alert tone="danger" className="sm:col-span-2">{details.error}</Alert> : null}
              {saved ? <Alert tone="success" className="sm:col-span-2">{t("common.saved")}</Alert> : null}
              <Field label={t("common.name")} className="sm:col-span-2">
                <Input name="full_name" required defaultValue={s.full_name} />
              </Field>
              <Field label={t("admin.section")}>
                <Select name="section_id" defaultValue={s.section_id ?? ""}>
                  <option value="">–</option>
                  {(sections.data ?? []).map((sec) => (
                    <option key={sec.id} value={sec.id}>
                      {sec.display_name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("admin.rollNo")}>
                <Input name="roll_no" defaultValue={s.roll_no ?? ""} />
              </Field>
              <Field label={t("admin.gender")}>
                <Select name="gender" defaultValue={s.gender ?? ""}>
                  <option value="">–</option>
                  {(["MALE", "FEMALE", "OTHER"] as const).map((g) => (
                    <option key={g} value={g}>
                      {t(`admin.gender${g}`)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("admin.dob")}>
                <Input name="date_of_birth" type="date" defaultValue={s.date_of_birth ?? ""} />
              </Field>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={details.busy}>
                  {t("common.save")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>{t("admin.guardians")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {guardians.error ? <Alert tone="danger">{guardians.error}</Alert> : null}
              {s.guardians.map((g) => (
                <div key={g.guardian_id} className="flex items-center justify-between rounded-md border border-border p-3">
                  <div>
                    <div className="font-medium">
                      {g.full_name} {g.is_primary ? <Badge tone="info">{t("admin.primary")}</Badge> : null}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {t(`admin.relation${g.relation}` as MessageKey)} · {g.phone}
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => unlink(g.guardian_id)}>
                    {t("admin.unlink")}
                  </Button>
                </div>
              ))}
              <form onSubmit={addGuardian} className="flex flex-wrap gap-2 border-t border-border pt-3">
                <Input name="full_name" required placeholder={t("common.name")} className="w-44" />
                <Input name="phone" required inputMode="tel" placeholder={t("common.phone")} className="w-40" />
                <Select name="relation" className="w-32" aria-label={t("admin.relation")}>
                  <option value="FATHER">{t("admin.relationFATHER")}</option>
                  <option value="MOTHER">{t("admin.relationMOTHER")}</option>
                  <option value="GUARDIAN">{t("admin.relationGUARDIAN")}</option>
                </Select>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" name="is_primary" /> {t("admin.primary")}
                </label>
                <Button type="submit" size="sm" disabled={guardians.busy}>
                  {t("admin.addGuardian")}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                {t("admin.hasPin")}:{" "}
                {s.has_pin ? <Badge tone="success">{t("admin.pinSet")}</Badge> : <Badge>{t("admin.pinNotSet")}</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={savePin} className="flex flex-wrap items-end gap-3">
                {pin.error ? <Alert tone="danger" className="w-full">{pin.error}</Alert> : null}
                {pinSaved ? <Alert tone="success" className="w-full">{t("admin.pinSaved")}</Alert> : null}
                <Field label={t("admin.newPin")}>
                  <Input name="pin" required inputMode="numeric" pattern="\d{4,8}" autoComplete="off" className="w-40" />
                </Field>
                <Button type="submit" disabled={pin.busy}>
                  {t("admin.setPin")}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
