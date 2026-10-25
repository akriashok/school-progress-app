"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { t } from "@/i18n";
import { Button } from "@/components/ui/button";
import { PageHeader, Spinner } from "@/components/ui/misc";
import { MarksGrid } from "@/components/marks-grid";

function Inner() {
  const params = useSearchParams();
  const router = useRouter();
  return (
    <>
      <PageHeader
        title={t("marks.title")}
        actions={
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft /> {t("common.back")}
          </Button>
        }
      />
      <MarksGrid examSubjectId={params.get("es") ?? ""} sectionId={params.get("section") ?? ""} />
    </>
  );
}

export default function ManagerMarksPage() {
  return (
    <React.Suspense fallback={<Spinner />}>
      <Inner />
    </React.Suspense>
  );
}
