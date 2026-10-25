"use client";

import * as React from "react";
import { Pencil, Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { useAction } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Alert, Empty, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export type FieldDef<T> = {
  key: keyof T & string;
  label: string;
  type?: "text" | "number" | "date" | "checkbox";
  required?: boolean;
  render?: (row: T) => React.ReactNode;
};

type Values = Record<string, string | number | boolean | null>;

function toValues<T>(fields: FieldDef<T>[], row?: T): Values {
  const v: Values = {};
  for (const f of fields) {
    const raw = row ? (row[f.key] as unknown) : undefined;
    v[f.key] = f.type === "checkbox" ? Boolean(raw) : raw === undefined || raw === null ? "" : (raw as string);
  }
  return v;
}

function clean<T>(fields: FieldDef<T>[], v: Values): Values {
  const out: Values = {};
  for (const f of fields) {
    const x = v[f.key];
    if (f.type === "number") out[f.key] = x === "" ? null : Number(x);
    else if (f.type === "checkbox") out[f.key] = Boolean(x);
    else out[f.key] = x === "" ? null : x;
  }
  return out;
}

function FieldInputs<T>({
  fields,
  values,
  onChange,
}: {
  fields: FieldDef<T>[];
  values: Values;
  onChange: (v: Values) => void;
}) {
  return (
    <>
      {fields.map((f) =>
        f.type === "checkbox" ? (
          <label key={f.key} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(values[f.key])}
              onChange={(e) => onChange({ ...values, [f.key]: e.target.checked })}
              className="h-4 w-4"
            />
            {f.label}
          </label>
        ) : (
          <Input
            key={f.key}
            aria-label={f.label}
            placeholder={f.label}
            type={f.type ?? "text"}
            required={f.required}
            value={String(values[f.key] ?? "")}
            onChange={(e) => onChange({ ...values, [f.key]: e.target.value })}
            className="min-w-32 flex-1"
          />
        ),
      )}
    </>
  );
}

/** A small list + create + inline edit + delete table for simple setup entities. */
export function CrudTable<T extends { id: string }>({
  rows,
  loading,
  fields,
  onCreate,
  onUpdate,
  onDelete,
  canEdit = true,
  extraActions,
}: {
  rows: T[] | undefined;
  loading: boolean;
  fields: FieldDef<T>[];
  onCreate: (v: Values) => Promise<unknown>;
  onUpdate?: (id: string, v: Values) => Promise<unknown>;
  onDelete?: (id: string) => Promise<unknown>;
  canEdit?: boolean;
  extraActions?: (row: T) => React.ReactNode;
}) {
  const [draft, setDraft] = React.useState<Values>(() => toValues(fields));
  const [editing, setEditing] = React.useState<{ id: string; values: Values } | null>(null);
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent) {
    e.preventDefault();
    const ok = await run(() => onCreate(clean(fields, draft)));
    if (ok !== undefined) setDraft(toValues(fields));
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing || !onUpdate) return;
    const ok = await run(() => onUpdate(editing.id, clean(fields, editing.values)));
    if (ok !== undefined) setEditing(null);
  }

  return (
    <div className="flex flex-col gap-4">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {canEdit ? (
        <Card>
          <CardContent className="p-4">
            <form onSubmit={create} className="flex flex-wrap items-center gap-3">
              <FieldInputs fields={fields} values={draft} onChange={setDraft} />
              <Button type="submit" disabled={busy}>
                {t("common.add")}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}
      <Card>
        {loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : !rows?.length ? (
          <div className="p-4">
            <Empty>{t("common.none")}</Empty>
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                {fields.map((f) => (
                  <TH key={f.key}>{f.label}</TH>
                ))}
                {canEdit || extraActions ? <TH className="text-right">{t("common.actions")}</TH> : null}
              </TR>
            </THead>
            <TBody>
              {rows.map((row) =>
                editing?.id === row.id ? (
                  <TR key={row.id}>
                    <TD colSpan={fields.length + 1}>
                      <form onSubmit={saveEdit} className="flex flex-wrap items-center gap-3">
                        <FieldInputs
                          fields={fields}
                          values={editing.values}
                          onChange={(values) => setEditing({ id: row.id, values })}
                        />
                        <Button type="submit" size="sm" disabled={busy}>
                          {t("common.save")}
                        </Button>
                        <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(null)}>
                          {t("common.cancel")}
                        </Button>
                      </form>
                    </TD>
                  </TR>
                ) : (
                  <TR key={row.id}>
                    {fields.map((f) => (
                      <TD key={f.key}>
                        {f.render
                          ? f.render(row)
                          : f.type === "checkbox"
                            ? row[f.key]
                              ? t("common.yes")
                              : t("common.no")
                            : String(row[f.key] ?? "–")}
                      </TD>
                    ))}
                    {canEdit || extraActions ? (
                      <TD className="text-right">
                        <div className="flex justify-end gap-1">
                          {extraActions?.(row)}
                          {canEdit && onUpdate ? (
                            <Button
                              size="icon"
                              variant="ghost"
                              aria-label={t("common.edit")}
                              onClick={() => setEditing({ id: row.id, values: toValues(fields, row) })}
                            >
                              <Pencil />
                            </Button>
                          ) : null}
                          {canEdit && onDelete ? (
                            <Button
                              size="icon"
                              variant="ghost"
                              aria-label={t("common.delete")}
                              onClick={() => {
                                if (confirm(t("common.confirmDelete"))) void run(() => onDelete(row.id));
                              }}
                            >
                              <Trash2 />
                            </Button>
                          ) : null}
                        </div>
                      </TD>
                    ) : null}
                  </TR>
                ),
              )}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
