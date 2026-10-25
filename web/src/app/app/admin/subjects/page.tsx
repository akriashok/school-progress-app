"use client";

import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useQuery } from "@/lib/hooks";
import { getSubjects, type Subject } from "@/lib/queries";
import { CrudTable, type FieldDef } from "@/components/crud-table";
import { PageHeader } from "@/components/ui/misc";

type SubjectBody = { name: string; code?: string | null };

export default function SubjectsPage() {
  const q = useQuery(getSubjects, []);
  const fields: FieldDef<Subject>[] = [
    { key: "name", label: t("admin.subjectName"), required: true },
    { key: "code", label: t("admin.subjectCode") },
  ];
  const after = <T,>(r: T) => {
    q.reload();
    return r;
  };
  return (
    <>
      <PageHeader title={t("admin.subjectsTitle")} />
      <CrudTable
        rows={q.data}
        loading={q.loading}
        fields={fields}
        onCreate={(v) => unwrap(api.POST("/api/v1/subjects", { body: v as SubjectBody })).then(after)}
        onUpdate={(id, v) =>
          unwrap(
            api.PUT("/api/v1/subjects/{subject_id}", { params: { path: { subject_id: id } }, body: v as SubjectBody }),
          ).then(after)
        }
        onDelete={(id) =>
          unwrap(api.DELETE("/api/v1/subjects/{subject_id}", { params: { path: { subject_id: id } } })).then(after)
        }
      />
    </>
  );
}
