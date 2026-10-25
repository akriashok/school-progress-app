"use client";

import * as React from "react";
import { Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap, type Schemas } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { num } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Alert, Badge, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

type Scale = Schemas["GradeScaleOut"];
type Band = { grade: string; min_percent: string; max_percent: string; grade_point: string };

function ScaleEditor({ scale, onSaved }: { scale: Scale; onSaved: () => void }) {
  const [bands, setBands] = React.useState<Band[]>(
    scale.bands.map((b) => ({
      grade: b.grade,
      min_percent: num(b.min_percent),
      max_percent: num(b.max_percent),
      grade_point: b.grade_point === null ? "" : num(b.grade_point),
    })),
  );
  const { busy, error, run } = useAction();
  const [saved, setSaved] = React.useState(false);

  async function save() {
    setSaved(false);
    const ok = await run(() =>
      unwrap(
        api.PUT("/api/v1/grade-scales/{scale_id}", {
          params: { path: { scale_id: scale.id } },
          body: {
            name: scale.name,
            is_default: scale.is_default,
            bands: bands.map((b) => ({
              grade: b.grade,
              min_percent: b.min_percent,
              max_percent: b.max_percent,
              grade_point: b.grade_point === "" ? null : b.grade_point,
            })),
          },
        }),
      ),
    );
    if (ok) {
      setSaved(true);
      onSaved();
    }
  }

  const update = (i: number, patch: Partial<Band>) => setBands((bs) => bs.map((b, j) => (j === i ? { ...b, ...patch } : b)));

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-3">
        <CardTitle>{scale.name}</CardTitle>
        {scale.is_default ? <Badge tone="success">{t("admin.current")}</Badge> : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {saved ? <Alert tone="success">{t("common.saved")}</Alert> : null}
        <Table>
          <THead>
            <TR>
              <TH>{t("admin.grade")}</TH>
              <TH>{t("admin.minPercent")}</TH>
              <TH>{t("admin.maxPercent")}</TH>
              <TH>{t("admin.gradePoint")}</TH>
              <TH />
            </TR>
          </THead>
          <TBody>
            {bands.map((b, i) => (
              <TR key={i}>
                {(["grade", "min_percent", "max_percent", "grade_point"] as const).map((k) => (
                  <TD key={k}>
                    <Input
                      value={b[k]}
                      type={k === "grade" ? "text" : "number"}
                      step="0.01"
                      onChange={(e) => update(i, { [k]: e.target.value })}
                      className="h-9 w-28"
                      aria-label={k}
                    />
                  </TD>
                ))}
                <TD>
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label={t("common.delete")}
                    onClick={() => setBands((bs) => bs.filter((_, j) => j !== i))}
                  >
                    <Trash2 />
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setBands((bs) => [...bs, { grade: "", min_percent: "", max_percent: "", grade_point: "" }])}
          >
            {t("admin.addBand")}
          </Button>
          <Button onClick={save} disabled={busy}>
            {t("common.save")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function GradeScalesPage() {
  const scales = useQuery(() => unwrap(api.GET("/api/v1/grade-scales")), []);
  return (
    <>
      <PageHeader title={t("admin.gradeTitle")} description={t("admin.gradeBody")} />
      {scales.loading ? (
        <Spinner />
      ) : (
        <div className="flex flex-col gap-4">
          {(scales.data ?? []).map((s) => (
            <ScaleEditor key={s.id} scale={s} onSaved={scales.reload} />
          ))}
        </div>
      )}
    </>
  );
}
