"use client";

import * as React from "react";
import { Pencil, Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap, type Schemas } from "@/lib/api";
import { useAction, useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Alert, Empty, PageHeader, Spinner } from "@/components/ui/misc";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Pager } from "@/components/pager";

type Guardian = Schemas["GuardianOut"];
const PAGE_SIZE = 50;

export default function ParentsPage() {
  const [q, setQ] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [editing, setEditing] = React.useState<Guardian | null>(null);
  const list = useQuery(
    () => unwrap(api.GET("/api/v1/guardians", { params: { query: { q: q || undefined, page, page_size: PAGE_SIZE } } })),
    [q, page],
  );
  const { busy, error, run } = useAction();

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    const ok = await run(() =>
      unwrap(
        api.POST("/api/v1/guardians", {
          body: {
            full_name: String(f.get("full_name")),
            phone: String(f.get("phone")),
            email: (f.get("email") as string) || null,
          },
        }),
      ),
    );
    if (ok) {
      form.reset();
      list.reload();
    }
  }

  async function saveEdit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editing) return;
    const f = new FormData(e.currentTarget);
    const ok = await run(() =>
      unwrap(
        api.PATCH("/api/v1/guardians/{guardian_id}", {
          params: { path: { guardian_id: editing.id } },
          body: { full_name: String(f.get("full_name")), email: (f.get("email") as string) || null },
        }),
      ),
    );
    if (ok) {
      setEditing(null);
      list.reload();
    }
  }

  async function remove(id: string) {
    if (!confirm(t("common.confirmDelete"))) return;
    await run(() => unwrap(api.DELETE("/api/v1/guardians/{guardian_id}", { params: { path: { guardian_id: id } } })));
    list.reload();
  }

  return (
    <>
      <PageHeader
        title={t("admin.parentsTitle")}
        actions={
          <Input
            type="search"
            placeholder={t("common.search")}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            className="w-60"
          />
        }
      />
      {error ? <Alert tone="danger" className="mb-4">{error}</Alert> : null}
      <Card className="mb-4">
        <CardContent className="p-4">
          <form onSubmit={create} className="flex flex-wrap gap-3">
            <Input name="full_name" required placeholder={t("common.name")} className="w-56" />
            <Input name="phone" required inputMode="tel" placeholder={t("common.phone")} className="w-44" />
            <Input name="email" type="email" placeholder={t("common.email")} className="w-56" />
            <Button type="submit" disabled={busy}>
              {t("common.add")}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Card>
        {list.loading ? (
          <div className="p-8 text-center">
            <Spinner />
          </div>
        ) : !list.data?.items.length ? (
          <div className="p-4">
            <Empty>{t("common.none")}</Empty>
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <TR>
                  <TH>{t("common.name")}</TH>
                  <TH>{t("common.phone")}</TH>
                  <TH>{t("common.email")}</TH>
                  <TH className="text-right">{t("common.actions")}</TH>
                </TR>
              </THead>
              <TBody>
                {list.data.items.map((g) =>
                  editing?.id === g.id ? (
                    <TR key={g.id}>
                      <TD colSpan={4}>
                        <form onSubmit={saveEdit} className="flex flex-wrap gap-3">
                          <Input name="full_name" required defaultValue={g.full_name} className="w-56" />
                          <Input name="email" type="email" defaultValue={g.email ?? ""} className="w-56" />
                          <Button size="sm" type="submit" disabled={busy}>
                            {t("common.save")}
                          </Button>
                          <Button size="sm" type="button" variant="ghost" onClick={() => setEditing(null)}>
                            {t("common.cancel")}
                          </Button>
                        </form>
                      </TD>
                    </TR>
                  ) : (
                    <TR key={g.id}>
                      <TD className="font-medium">{g.full_name}</TD>
                      <TD className="tabular-nums">{g.phone}</TD>
                      <TD>{g.email ?? "–"}</TD>
                      <TD className="text-right">
                        <Button size="icon" variant="ghost" aria-label={t("common.edit")} onClick={() => setEditing(g)}>
                          <Pencil />
                        </Button>
                        <Button size="icon" variant="ghost" aria-label={t("common.delete")} onClick={() => remove(g.id)}>
                          <Trash2 />
                        </Button>
                      </TD>
                    </TR>
                  ),
                )}
              </TBody>
            </Table>
            <Pager page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
