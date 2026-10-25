"use client";

import * as React from "react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/input";
import { Alert } from "@/components/ui/misc";

export function DemoForm() {
  const { busy, error, run } = useAction();
  const [done, setDone] = React.useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const students = f.get("students") ? Number(f.get("students")) : null;
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/public/demo-requests", {
          body: {
            name: String(f.get("name")),
            school_name: String(f.get("school_name")),
            phone: String(f.get("phone")),
            city: (f.get("city") as string) || null,
            students,
            message: (f.get("message") as string) || null,
          },
        }),
      ),
    );
    if (ok) setDone(true);
  }

  if (done) return <Alert tone="success">{t("landing.demoThanks")}</Alert>;

  return (
    <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
      <Field label={t("landing.demoName")}>
        <Input name="name" required maxLength={150} autoComplete="name" />
      </Field>
      <Field label={t("common.phone")}>
        <Input name="phone" required inputMode="tel" autoComplete="tel" placeholder="98765 43210" />
      </Field>
      <Field label={t("landing.demoSchool")} className="sm:col-span-2">
        <Input name="school_name" required maxLength={200} />
      </Field>
      <Field label={t("landing.demoCity")}>
        <Input name="city" maxLength={80} />
      </Field>
      <Field label={t("landing.demoStudents")}>
        <Input name="students" type="number" min={0} max={100000} />
      </Field>
      <Field label={t("landing.demoMessage")} className="sm:col-span-2">
        <Textarea name="message" maxLength={2000} />
      </Field>
      {error ? (
        <Alert tone="danger" className="sm:col-span-2">
          {error}
        </Alert>
      ) : null}
      <div className="sm:col-span-2">
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? t("common.saving") : t("landing.demoSubmit")}
        </Button>
      </div>
    </form>
  );
}
