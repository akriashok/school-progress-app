"use client";

import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useQuery } from "@/lib/hooks";
import { getClasses, type SchoolClass } from "@/lib/queries";
import { CrudTable, type FieldDef } from "@/components/crud-table";
import { PageHeader } from "@/components/ui/misc";

type ClassBody = { name: string; sort_order: number };

export default function ClassesPage() {
  const q = useQuery(getClasses, []);
  const fields: FieldDef<SchoolClass>[] = [
    { key: "name", label: t("admin.className"), required: true },
    { key: "sort_order", label: t("admin.sortOrder"), type: "number", required: true },
  ];
  const after = <T,>(r: T) => {
    q.reload();
    return r;
  };
  return (
    <>
      <PageHeader title={t("admin.classesTitle")} />
      <CrudTable
        rows={q.data}
        loading={q.loading}
        fields={fields}
        onCreate={(v) => unwrap(api.POST("/api/v1/classes", { body: v as ClassBody })).then(after)}
        onUpdate={(id, v) =>
          unwrap(api.PUT("/api/v1/classes/{class_id}", { params: { path: { class_id: id } }, body: v as ClassBody })).then(
            after,
          )
        }
        onDelete={(id) => unwrap(api.DELETE("/api/v1/classes/{class_id}", { params: { path: { class_id: id } } })).then(after)}
      />
    </>
  );
}
