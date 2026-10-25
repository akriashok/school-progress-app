"use client";

import { t } from "@/i18n";
import { api, unwrap } from "@/lib/api";
import { useQuery } from "@/lib/hooks";
import { getYears, type Year } from "@/lib/queries";
import { CrudTable, type FieldDef } from "@/components/crud-table";
import { Badge, PageHeader } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";

type YearBody = { name: string; start_date: string; end_date: string; is_current: boolean };

export default function YearsPage() {
  const q = useQuery(getYears, []);
  const fields: FieldDef<Year>[] = [
    { key: "name", label: t("admin.yearName"), required: true },
    { key: "start_date", label: t("admin.startDate"), type: "date", required: true },
    { key: "end_date", label: t("admin.endDate"), type: "date", required: true },
    {
      key: "is_current",
      label: t("admin.isCurrent"),
      type: "checkbox",
      render: (y) => (y.is_current ? <Badge tone="success">{t("admin.current")}</Badge> : null),
    },
  ];
  const after = <T,>(r: T) => {
    q.reload();
    return r;
  };
  return (
    <>
      <PageHeader title={t("admin.yearsTitle")} />
      <CrudTable
        rows={q.data}
        loading={q.loading}
        fields={fields}
        onCreate={(v) => unwrap(api.POST("/api/v1/academic-years", { body: v as YearBody })).then(after)}
        onUpdate={(id, v) =>
          unwrap(
            api.PUT("/api/v1/academic-years/{year_id}", { params: { path: { year_id: id } }, body: v as YearBody }),
          ).then(after)
        }
        onDelete={(id) =>
          unwrap(api.DELETE("/api/v1/academic-years/{year_id}", { params: { path: { year_id: id } } })).then(after)
        }
        extraActions={(y) =>
          y.is_current ? null : (
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                unwrap(
                  api.PUT("/api/v1/academic-years/{year_id}", {
                    params: { path: { year_id: y.id } },
                    body: { name: y.name, start_date: y.start_date, end_date: y.end_date, is_current: true },
                  }),
                ).then(q.reload)
              }
            >
              {t("admin.makeCurrent")}
            </Button>
          )
        }
      />
    </>
  );
}
