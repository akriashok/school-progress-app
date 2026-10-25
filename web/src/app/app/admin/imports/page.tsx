"use client";

import { Download } from "lucide-react";
import { t } from "@/i18n";
import { downloadFile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/misc";
import { ImportPanel } from "@/components/import-panel";

export default function ImportsPage() {
  return (
    <>
      <PageHeader title={t("imports.title")} description={t("imports.body")} />
      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>{t("imports.students")}</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadFile("/api/v1/imports/templates/students", "students_template.xlsx")}
            >
              <Download /> {t("imports.template")}
            </Button>
          </CardHeader>
          <CardContent>
            <ImportPanel
              uploadPath="/api/v1/imports/students"
              previewColumns={[
                { key: "admission_no", label: t("admin.admissionNo") },
                { key: "full_name", label: t("common.name") },
                { key: "class", label: t("admin.class") },
                { key: "section", label: t("admin.section") },
                { key: "roll_no", label: t("admin.rollNo") },
              ]}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>{t("imports.teachers")}</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadFile("/api/v1/imports/templates/teachers", "teachers_template.xlsx")}
            >
              <Download /> {t("imports.template")}
            </Button>
          </CardHeader>
          <CardContent>
            <ImportPanel
              uploadPath="/api/v1/imports/teachers"
              previewColumns={[
                { key: "full_name", label: t("common.name") },
                { key: "phone", label: t("common.phone") },
                { key: "designation", label: t("admin.designation") },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
