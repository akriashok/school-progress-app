"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { errorMessage, useQuery } from "@/lib/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, Empty, PageHeader, Spinner } from "@/components/ui/misc";

export default function FamilyHome() {
  const me = useMe();
  const router = useRouter();
  const isParent = me.role === "PARENT";
  const children = useQuery(() => unwrap(api.GET("/api/v1/children")), [isParent], isParent);

  React.useEffect(() => {
    if (!isParent && me.student_id) router.replace(`/app/family/${me.student_id}`);
    // A parent with exactly one child goes straight to that child.
    if (isParent && children.data?.length === 1) router.replace(`/app/family/${children.data[0].student_id}`);
  }, [isParent, me.student_id, children.data, router]);

  if (!isParent || children.loading) return <Spinner />;
  if (children.error) return <Alert tone="danger">{errorMessage(children.error)}</Alert>;

  return (
    <>
      <PageHeader title={t("family.childrenTitle")} description={t("family.pickChild")} />
      {!children.data?.length ? (
        <Empty>{t("family.noChildren")}</Empty>
      ) : (
        <div className="flex flex-col gap-3">
          {children.data.map((c) => (
            <Link key={c.student_id} href={`/app/family/${c.student_id}`}>
              <Card className="transition-colors hover:border-primary">
                <CardContent className="flex items-center gap-4 p-5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-lg font-semibold text-secondary-foreground">
                    {c.full_name.charAt(0)}
                  </div>
                  <div className="flex-1">
                    <div className="text-lg font-semibold">{c.full_name}</div>
                    <div className="text-sm text-muted-foreground">
                      {[c.section_name, c.school_name].filter(Boolean).join(" · ")}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground" aria-hidden />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
