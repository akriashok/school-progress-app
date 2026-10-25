"use client";

import * as React from "react";
import { Download, Upload } from "lucide-react";
import { t } from "@/i18n";
import { api, downloadFile, unwrap, uploadFile, type Schemas } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Alert, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export type ImportOut = Schemas["ImportOut"];

async function waitForValidation(id: string): Promise<ImportOut> {
  for (let i = 0; i < 60; i++) {
    const imp = await unwrap(api.GET("/api/v1/imports/{import_id}", { params: { path: { import_id: id } } }));
    if (imp.status !== "UPLOADED" && imp.status !== "VALIDATING") return imp;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error("timeout");
}

/** Upload -> background validation -> preview with row errors -> commit. */
export function ImportPanel({
  uploadPath,
  previewColumns,
  onCommitted,
  commitReason,
}: {
  uploadPath: string;
  previewColumns: { key: string; label: string }[];
  onCommitted?: (imp: ImportOut) => void;
  commitReason?: string | null;
}) {
  const [imp, setImp] = React.useState<ImportOut | null>(null);
  const [validating, setValidating] = React.useState(false);
  const { busy, error, run } = useAction();
  const fileRef = React.useRef<HTMLInputElement>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImp(null);
    setValidating(true);
    const result = await run(async () => waitForValidation((await uploadFile<ImportOut>(uploadPath, file)).id));
    setValidating(false);
    if (result) setImp(result);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function commit() {
    if (!imp) return;
    const done = await run(() =>
      unwrap(
        api.POST("/api/v1/imports/{import_id}/commit", {
          params: { path: { import_id: imp.id } },
          body: { reason: commitReason ?? null },
        }),
      ),
    );
    if (done) {
      setImp(done);
      onCommitted?.(done);
    }
  }

  const result = imp?.result as { created?: number; updated?: number } | null | undefined;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <input ref={fileRef} type="file" accept=".xlsx,.csv" onChange={onFile} className="hidden" id={`f-${uploadPath}`} />
        <Button asChild variant="outline" disabled={busy}>
          <label htmlFor={`f-${uploadPath}`} className="cursor-pointer">
            <Upload /> {t("imports.upload")}
          </label>
        </Button>
        <span className="ml-3 text-sm text-muted-foreground">{t("imports.chooseFile")}</span>
      </div>
      {validating ? (
        <div className="flex items-center gap-2 text-sm">
          <Spinner /> {t("imports.validating")}
        </div>
      ) : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {imp?.status === "FAILED" ? (
        <Alert tone="danger">
          {t("imports.failed")} {imp.errors[0]?.message as string}
        </Alert>
      ) : null}
      {imp?.status === "COMMITTED" ? (
        <Alert tone="success">
          {t("imports.committed", { created: result?.created ?? 0, updated: result?.updated ?? 0 })}
        </Alert>
      ) : null}
      {imp && imp.status === "READY" ? (
        <>
          <Alert tone={imp.error_count ? "warning" : "success"}>
            {t("imports.summary", { valid: imp.valid_rows ?? 0, total: imp.total_rows ?? 0 })}
            {imp.error_count ? ` ${t("imports.fixAndRetry")}` : ""}
          </Alert>
          {imp.error_count ? (
            <div className="rounded-md border border-border">
              <div className="flex items-center justify-between border-b border-border p-3">
                <span className="text-sm font-medium">{t("imports.errorsTitle", { n: imp.error_count })}</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadFile(`/api/v1/imports/${imp.id}/errors.xlsx`, "import-errors.xlsx")}
                >
                  <Download /> {t("imports.errorsFile")}
                </Button>
              </div>
              <div className="max-h-72 overflow-y-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>{t("imports.row")}</TH>
                      <TH>{t("imports.column")}</TH>
                      <TH>{t("imports.problem")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {imp.errors.map((e, i) => (
                      <TR key={i}>
                        <TD className="tabular-nums">{String(e.row ?? "–")}</TD>
                        <TD>{String(e.column ?? "–")}</TD>
                        <TD className="text-destructive">{String(e.message)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            </div>
          ) : null}
          {imp.preview.length ? (
            <div className="rounded-md border border-border">
              <div className="border-b border-border p-3 text-sm font-medium">{t("imports.preview")}</div>
              <div className="max-h-72 overflow-y-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>{t("imports.row")}</TH>
                      {previewColumns.map((c) => (
                        <TH key={c.key}>{c.label}</TH>
                      ))}
                    </TR>
                  </THead>
                  <TBody>
                    {imp.preview.map((r, i) => (
                      <TR key={i}>
                        <TD className="tabular-nums">{String(r.row)}</TD>
                        {previewColumns.map((c) => (
                          <TD key={c.key}>{String(r[c.key] ?? "–")}</TD>
                        ))}
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            </div>
          ) : null}
          {imp.valid_rows ? (
            <div>
              <Button onClick={commit} disabled={busy} size="lg">
                {t("imports.commit", { n: imp.valid_rows })}
              </Button>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
