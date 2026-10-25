"use client";

import { useRouter } from "next/navigation";
import { t } from "@/i18n";
import { homeFor, useAuth, useMe } from "@/lib/auth";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, PageHeader } from "@/components/ui/misc";

export default function ProfilePage() {
  const me = useMe();
  const auth = useAuth();
  const router = useRouter();
  const { busy, error, run } = useAction();

  async function switchTo(roleId: string) {
    const next = await run(() => auth.switchRole(roleId));
    if (next) router.replace(next.consent_required ? "/consent" : homeFor(next.role));
  }

  return (
    <>
      <PageHeader title={t("profile.title")} />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("profile.signedInAs")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
              <dt className="text-muted-foreground">{t("common.name")}</dt>
              <dd className="font-medium">{me.full_name}</dd>
              <dt className="text-muted-foreground">{t("profile.role")}</dt>
              <dd>{t(`roles.${me.role}`)}</dd>
              {me.school_name ? (
                <>
                  <dt className="text-muted-foreground">{t("profile.school")}</dt>
                  <dd>
                    {me.school_name} ({me.school_code})
                  </dd>
                </>
              ) : null}
            </dl>
            <Button
              className="mt-6"
              variant="outline"
              onClick={() => auth.logout().then(() => router.replace("/login"))}
            >
              {t("nav.logout")}
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t("profile.otherRoles")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {error ? <Alert tone="danger">{error}</Alert> : null}
            {me.other_roles.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("profile.noOtherRoles")}</p>
            ) : (
              me.other_roles.map((r) => (
                <div key={r.role_id} className="flex items-center justify-between rounded-md border border-border p-3">
                  <div>
                    <div className="font-medium">{t(`roles.${r.role}`)}</div>
                    {r.school_name ? <div className="text-sm text-muted-foreground">{r.school_name}</div> : null}
                  </div>
                  <Button size="sm" variant="outline" disabled={busy} onClick={() => switchTo(r.role_id)}>
                    {t("profile.switchTo")}
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
