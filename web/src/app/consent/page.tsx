"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { useAction, useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, Spinner } from "@/components/ui/misc";
import { Logo } from "@/components/public-shell";

export default function ConsentPage() {
  const router = useRouter();
  const auth = useAuth();
  const { busy, error, run } = useAction();
  const isParent = auth.status === "authenticated" && auth.me.role === "PARENT";
  const consent = useQuery(() => unwrap(api.GET("/api/v1/consent/current")), [isParent], isParent);

  React.useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
    if (auth.status === "authenticated" && !auth.me.consent_required) router.replace(homeFor(auth.me.role));
  }, [auth, router]);

  async function accept() {
    if (!consent.data) return;
    const version = consent.data.version;
    const ok = await run(() => unwrap(api.POST("/api/v1/consent/accept", { body: { version } })));
    if (ok) {
      await auth.reloadMe();
      router.replace("/app/family");
    }
  }

  if (auth.status !== "authenticated" || consent.loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-10">
      <Logo />
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle className="text-xl">{t("consent.title")}</CardTitle>
          <CardDescription>{t("consent.intro", { school: auth.me.school_name ?? "" })}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          {consent.data ? (
            <>
              <div className="max-h-80 overflow-y-auto whitespace-pre-line rounded-md border border-border bg-muted/40 p-4 text-base leading-relaxed">
                {consent.data.body}
              </div>
              <p className="text-xs text-muted-foreground">{t("consent.version", { version: consent.data.version })}</p>
              <div className="flex gap-3">
                <Button size="lg" onClick={accept} disabled={busy}>
                  {t("consent.accept")}
                </Button>
                <Button size="lg" variant="outline" onClick={() => auth.logout().then(() => router.replace("/"))}>
                  {t("nav.logout")}
                </Button>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
