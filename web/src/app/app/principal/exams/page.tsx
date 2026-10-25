"use client";

import Link from "next/link";
import { t } from "@/i18n";
import { useQuery } from "@/lib/hooks";
import { currentYear, getExams, getYears } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export default function PrincipalExamsPage() {
  const years = useQuery(getYears, []);
  const year = currentYear(years.data);
  const exams = useQuery(() => getExams(year?.id), [year?.id], Boolean(year));
  return (
    <>
      <PageHeader title={t("principal.examsTitle")} description={year?.name} />
      {exams.loading || years.loading ? (
        <Spinner />
      ) : !exams.data?.length ? (
        <Empty>{t("common.none")}</Empty>
      ) : (
        <Card>
          <Table>
            <THead>
              <TR>
                <TH>{t("admin.sequence")}</TH>
                <TH>{t("principal.exam")}</TH>
                <TH />
              </TR>
            </THead>
            <TBody>
              {exams.data.map((ex) => (
                <TR key={ex.id}>
                  <TD className="tabular-nums">{ex.sequence}</TD>
                  <TD className="font-medium">{ex.name}</TD>
                  <TD className="text-right">
                    <Button asChild size="sm">
                      <Link href={`/app/principal/exams/${ex.id}`}>{t("principal.examStatus")}</Link>
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
      )}
    </>
  );
}
