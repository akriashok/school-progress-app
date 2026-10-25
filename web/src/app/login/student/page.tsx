"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/misc";
import { Logo } from "@/components/public-shell";

function StudentLoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const auth = useAuth();
  const { busy, error, run } = useAction();

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const tokens = await run(() =>
      unwrap(
        api.POST("/api/v1/auth/student/login", {
          body: {
            school_code: String(f.get("school_code")).trim(),
            admission_no: String(f.get("admission_no")).trim(),
            pin: String(f.get("pin")).trim(),
            client: "web",
          },
        }),
      ),
    );
    if (!tokens) return;
    const me = await auth.startSession(tokens.access_token);
    router.replace(homeFor(me.role));
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <Field label={t("login.schoolCode")}>
        <Input
          name="school_code"
          required
          defaultValue={params.get("school") ?? ""}
          autoCapitalize="characters"
          className="h-12 text-lg uppercase"
        />
      </Field>
      <Field label={t("login.admissionNo")}>
        <Input name="admission_no" required className="h-12 text-lg" />
      </Field>
      <Field label={t("login.pin")}>
        <Input
          name="pin"
          required
          type="password"
          inputMode="numeric"
          pattern="\d{4,8}"
          autoComplete="current-password"
          className="h-12 text-lg tracking-widest"
        />
      </Field>
      <Button type="submit" size="lg" disabled={busy}>
        {t("login.studentSubmit")}
      </Button>
    </form>
  );
}

export default function StudentLoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-10">
      <Logo />
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">{t("login.studentTitle")}</CardTitle>
          <CardDescription>{t("login.studentSubtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <React.Suspense>
            <StudentLoginForm />
          </React.Suspense>
          <Link href="/login" className="text-center text-sm text-primary hover:underline">
            {t("login.staffLink")}
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
