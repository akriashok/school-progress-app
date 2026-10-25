"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { t } from "@/i18n";
import { api, unwrap, type Schemas } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/misc";
import { Logo } from "@/components/public-shell";

type Step = { kind: "phone" } | { kind: "otp"; phone: string } | { kind: "role"; ticket: string; roles: Schemas["RoleOption"][] };

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [step, setStep] = React.useState<Step>({ kind: "phone" });
  const { busy, error, setError, run } = useAction();

  React.useEffect(() => {
    if (auth.status === "authenticated") router.replace(auth.me.consent_required ? "/consent" : homeFor(auth.me.role));
  }, [auth, router]);

  async function pickRole(ticket: string, roleId: string) {
    const tokens = await run(() =>
      unwrap(api.POST("/api/v1/auth/session", { body: { ticket, role_id: roleId, client: "web" } })),
    );
    if (!tokens) return;
    const me = await auth.startSession(tokens.access_token);
    router.replace(me.consent_required ? "/consent" : homeFor(me.role));
  }

  async function sendOtp(phone: string) {
    const ok = await run(() => unwrap(api.POST("/api/v1/auth/otp/request", { body: { phone } })));
    if (ok) setStep({ kind: "otp", phone });
  }

  async function onPhone(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await sendOtp(String(new FormData(e.currentTarget).get("phone")).trim());
  }

  async function onOtp(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (step.kind !== "otp") return;
    const otp = String(new FormData(e.currentTarget).get("otp")).trim();
    const res = await run(() => unwrap(api.POST("/api/v1/auth/otp/verify", { body: { phone: step.phone, otp } })));
    if (!res) return;
    if (res.roles.length === 0) {
      setError(t("login.noRoles"));
      return;
    }
    if (res.roles.length === 1) {
      await pickRole(res.ticket, res.roles[0].role_id);
      return;
    }
    setStep({ kind: "role", ticket: res.ticket, roles: res.roles });
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-10">
      <Logo />
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">{step.kind === "role" ? t("login.pickRole") : t("login.title")}</CardTitle>
          <CardDescription>{step.kind === "role" ? t("login.pickRoleHint") : t("login.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {error ? <Alert tone="danger">{error}</Alert> : null}

          {step.kind === "phone" ? (
            <form onSubmit={onPhone} className="flex flex-col gap-4">
              <Field label={t("login.phone")} hint={t("login.phoneHint")}>
                <Input
                  name="phone"
                  required
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="98765 43210"
                  className="h-12 text-lg"
                  autoFocus
                />
              </Field>
              <Button type="submit" size="lg" disabled={busy}>
                {t("login.sendOtp")}
              </Button>
            </form>
          ) : null}

          {step.kind === "otp" ? (
            <form onSubmit={onOtp} className="flex flex-col gap-4">
              <Alert>{t("login.otpSent", { phone: step.phone })}</Alert>
              <Field label={t("login.otp")}>
                <Input
                  name="otp"
                  required
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="\d{6}"
                  maxLength={6}
                  className="h-12 text-center text-2xl tracking-[0.5em]"
                  autoFocus
                />
              </Field>
              <Button type="submit" size="lg" disabled={busy}>
                {t("login.verify")}
              </Button>
              <div className="flex justify-between text-sm">
                <button type="button" className="text-primary hover:underline" onClick={() => setStep({ kind: "phone" })}>
                  {t("login.changeNumber")}
                </button>
                <button type="button" className="text-primary hover:underline" disabled={busy} onClick={() => sendOtp(step.phone)}>
                  {t("login.resend")}
                </button>
              </div>
            </form>
          ) : null}

          {step.kind === "role" ? (
            <ul className="flex flex-col gap-2">
              {step.roles.map((r) => (
                <li key={r.role_id}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => pickRole(step.ticket, r.role_id)}
                    className="w-full rounded-md border border-border p-4 text-left transition-colors hover:border-primary hover:bg-secondary"
                  >
                    <div className="font-medium">{t(`roles.${r.role}`)}</div>
                    {r.school_name ? <div className="text-sm text-muted-foreground">{r.school_name}</div> : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          <Link href="/login/student" className="text-center text-sm text-primary hover:underline">
            {t("login.studentLink")}
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
