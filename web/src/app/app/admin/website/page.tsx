"use client";

import * as React from "react";
import { ExternalLink, ImagePlus, Plus, Trash2 } from "lucide-react";
import { t } from "@/i18n";
import { api, unwrap, uploadFile, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { errorMessage, useAction, useQuery } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { Alert, PageHeader, Spinner } from "@/components/ui/misc";

type Content = Schemas["WebsiteContent"];
const ICONS = ["book", "computer", "playground", "bus", "music", "palette", "trophy", "flask", "heart", "shield"] as const;

function ImagePicker({ code, value, onChange }: { code: string; value?: string | null; onChange: (id: string | null) => void }) {
  const { busy, error, run } = useAction();
  const ref = React.useRef<HTMLInputElement>(null);
  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = await run(() => uploadFile<{ image_id: string }>("/api/v1/school/website/images", file));
    if (res) onChange(res.image_id);
    if (ref.current) ref.current.value = "";
  }
  return (
    <div className="flex items-center gap-3">
      {value ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={`/api/v1/public/schools/${code}/images/${value}`} alt="" className="h-16 w-24 rounded-md border border-border object-cover" />
      ) : (
        <div className="flex h-16 w-24 items-center justify-center rounded-md border border-dashed border-border text-muted-foreground">
          <ImagePlus className="h-5 w-5" aria-hidden />
        </div>
      )}
      <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onFile} />
      <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => ref.current?.click()}>
        {busy ? <Spinner className="h-4 w-4" /> : t("website.upload")}
      </Button>
      {value ? (
        <Button type="button" size="sm" variant="ghost" onClick={() => onChange(null)}>
          {t("website.remove")}
        </Button>
      ) : null}
      {error ? <span className="text-xs text-destructive">{error}</span> : null}
    </div>
  );
}

function ListSection<T>({
  title,
  items,
  max,
  blank,
  onChange,
  render,
}: {
  title: string;
  items: T[];
  max: number;
  blank: T;
  onChange: (items: T[]) => void;
  render: (item: T, set: (patch: Partial<T>) => void) => React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <Button type="button" size="sm" variant="outline" disabled={items.length >= max} onClick={() => onChange([...items, blank])}>
          <Plus /> {t("website.addItem")}
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {items.map((item, i) => (
          <div key={i} className="relative rounded-md border border-border p-4">
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="absolute right-2 top-2"
              aria-label={t("website.remove")}
              onClick={() => onChange(items.filter((_, j) => j !== i))}
            >
              <Trash2 />
            </Button>
            <div className="grid gap-3 pr-10 md:grid-cols-2">
              {render(item, (patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x))))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function WebsiteEditorPage() {
  const me = useMe();
  const code = me.school_code ?? "";
  const q = useQuery(() => unwrap(api.GET("/api/v1/school/website")), []);
  const [c, setC] = React.useState<Content | null>(null);
  const { busy, error, run } = useAction();
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    if (q.data) setC(q.data);
  }, [q.data]);

  if (q.loading || !c) return q.error ? <Alert tone="danger">{errorMessage(q.error)}</Alert> : <Spinner />;
  const set = (patch: Partial<Content>) => {
    setSaved(false);
    setC({ ...c, ...patch });
  };
  const setContact = (patch: Partial<Content["contact"]>) => set({ contact: { ...c.contact, ...patch } });

  async function save() {
    if (!c) return;
    const res = await run(() => unwrap(api.PUT("/api/v1/school/website", { body: c })));
    if (res) {
      setC(res);
      setSaved(true);
    }
  }

  return (
    <>
      <PageHeader
        title={t("website.title")}
        description={t("website.body")}
        actions={
          <>
            <Button asChild variant="outline">
              <a href={`/schools/${code}`} target="_blank" rel="noopener noreferrer">
                <ExternalLink /> {t("website.view")}
              </a>
            </Button>
            <Button onClick={save} disabled={busy}>
              {busy ? t("common.saving") : t("common.save")}
            </Button>
          </>
        }
      />
      <div className="flex flex-col gap-4">
        <Alert tone="warning">{t("website.photoConsent")}</Alert>
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {saved ? <Alert tone="success">{t("website.saved")}</Alert> : null}

        <Card>
          <CardHeader><CardTitle>{t("website.hero")}</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label={t("website.tagline")}>
              <Input value={c.tagline ?? ""} maxLength={120} onChange={(e) => set({ tagline: e.target.value })} />
            </Field>
            <Field label={t("website.heroTitle")}>
              <Input value={c.hero_title ?? ""} maxLength={120} onChange={(e) => set({ hero_title: e.target.value })} />
            </Field>
            <Field label={t("website.heroSubtitle")} className="md:col-span-2">
              <Textarea value={c.hero_subtitle ?? ""} maxLength={2000} onChange={(e) => set({ hero_subtitle: e.target.value })} />
            </Field>
            <div className="md:col-span-2">
              <div className="mb-1.5 text-sm font-medium">{t("website.heroImage")}</div>
              <ImagePicker code={code} value={c.hero_image} onChange={(id) => set({ hero_image: id })} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t("website.about")}</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label={t("website.aboutTitle")} className="md:col-span-2">
              <Input value={c.about_title ?? ""} maxLength={120} onChange={(e) => set({ about_title: e.target.value })} />
            </Field>
            <Field label={t("website.aboutBody")} className="md:col-span-2">
              <Textarea rows={6} value={c.about_body ?? ""} maxLength={5000} onChange={(e) => set({ about_body: e.target.value })} />
            </Field>
            <Field label={t("website.excellence")} className="md:col-span-2">
              <Textarea
                rows={4}
                value={(c.excellence ?? []).join("\n")}
                onChange={(e) => set({ excellence: e.target.value.split("\n").slice(0, 10) })}
                onBlur={(e) => set({ excellence: e.target.value.split("\n").map((x) => x.trim()).filter(Boolean).slice(0, 10) })}
              />
            </Field>
            <div className="md:col-span-2">
              <div className="mb-1.5 text-sm font-medium">{t("website.aboutImage")}</div>
              <ImagePicker code={code} value={c.about_image} onChange={(id) => set({ about_image: id })} />
            </div>
          </CardContent>
        </Card>

        <ListSection
          title={t("website.highlights")}
          items={c.highlights ?? []}
          max={6}
          blank={{ title: "", body: "", image: null }}
          onChange={(highlights) => set({ highlights })}
          render={(h, setH) => (
            <>
              <Field label={t("website.title2")}><Input value={h.title} required maxLength={120} onChange={(e) => setH({ title: e.target.value })} /></Field>
              <ImagePicker code={code} value={h.image} onChange={(image) => setH({ image })} />
              <Field label={t("website.text")} className="md:col-span-2"><Textarea value={h.body ?? ""} maxLength={2000} onChange={(e) => setH({ body: e.target.value })} /></Field>
            </>
          )}
        />

        <ListSection
          title={t("website.stats")}
          items={c.stats ?? []}
          max={4}
          blank={{ value: "", label: "" }}
          onChange={(stats) => set({ stats })}
          render={(s, setS) => (
            <>
              <Field label={t("website.value")}><Input value={s.value} maxLength={12} placeholder="1200+" onChange={(e) => setS({ value: e.target.value })} /></Field>
              <Field label={t("website.label")}><Input value={s.label} maxLength={40} placeholder="Students" onChange={(e) => setS({ label: e.target.value })} /></Field>
            </>
          )}
        />

        <ListSection
          title={t("website.facilities")}
          items={c.facilities ?? []}
          max={8}
          blank={{ title: "", body: "", icon: "book", image: null }}
          onChange={(facilities) => set({ facilities })}
          render={(f, setF) => (
            <>
              <Field label={t("website.title2")}><Input value={f.title} maxLength={120} onChange={(e) => setF({ title: e.target.value })} /></Field>
              <Field label={t("website.icon")}>
                <Select value={f.icon ?? "book"} onChange={(e) => setF({ icon: e.target.value as (typeof ICONS)[number] })}>
                  {ICONS.map((i) => <option key={i} value={i}>{i}</option>)}
                </Select>
              </Field>
              <Field label={t("website.text")}><Textarea value={f.body ?? ""} maxLength={2000} onChange={(e) => setF({ body: e.target.value })} /></Field>
              <ImagePicker code={code} value={f.image} onChange={(image) => setF({ image })} />
            </>
          )}
        />

        <ListSection
          title={t("website.gallery")}
          items={c.gallery ?? []}
          max={24}
          blank={{ image: "", caption: "" }}
          onChange={(gallery) => set({ gallery })}
          render={(g, setG) => (
            <>
              <ImagePicker code={code} value={g.image || null} onChange={(image) => setG({ image: image ?? "" })} />
              <Field label={t("website.caption")}><Input value={g.caption ?? ""} maxLength={120} onChange={(e) => setG({ caption: e.target.value })} /></Field>
            </>
          )}
        />

        <ListSection
          title={t("website.leaders")}
          items={c.leaders ?? []}
          max={8}
          blank={{ name: "", role: "", bio: "", photo: null }}
          onChange={(leaders) => set({ leaders })}
          render={(l, setL) => (
            <>
              <Field label={t("website.personName")}><Input value={l.name} maxLength={120} onChange={(e) => setL({ name: e.target.value })} /></Field>
              <Field label={t("website.role")}><Input value={l.role ?? ""} maxLength={120} onChange={(e) => setL({ role: e.target.value })} /></Field>
              <Field label={t("website.bio")}><Textarea value={l.bio ?? ""} maxLength={2000} onChange={(e) => setL({ bio: e.target.value })} /></Field>
              <ImagePicker code={code} value={l.photo} onChange={(photo) => setL({ photo })} />
            </>
          )}
        />

        <Card>
          <CardHeader><CardTitle>{t("website.admissions")}</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input
                type="checkbox"
                className="h-4 w-4"
                checked={c.admissions?.open ?? false}
                onChange={(e) => set({ admissions: { ...c.admissions, open: e.target.checked } })}
              />
              {t("website.admissionsOpen")}
            </label>
            <Field label={t("website.title2")}>
              <Input value={c.admissions?.title ?? ""} maxLength={120} onChange={(e) => set({ admissions: { ...c.admissions, title: e.target.value } })} />
            </Field>
            <Field label={t("website.text")}>
              <Input value={c.admissions?.body ?? ""} maxLength={2000} onChange={(e) => set({ admissions: { ...c.admissions, body: e.target.value } })} />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("website.contact")}</CardTitle>
            <p className="text-sm text-muted-foreground">{t("website.contactNote")}</p>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label={t("website.whatsapp")}><Input inputMode="tel" value={c.contact?.whatsapp ?? ""} onChange={(e) => setContact({ whatsapp: e.target.value || null })} /></Field>
            <Field label={t("website.timings")}><Input value={c.contact?.timings ?? ""} maxLength={120} onChange={(e) => setContact({ timings: e.target.value })} /></Field>
            <Field label={t("website.facebook")}><Input value={c.contact?.facebook ?? ""} onChange={(e) => setContact({ facebook: e.target.value || null })} /></Field>
            <Field label={t("website.instagram")}><Input value={c.contact?.instagram ?? ""} onChange={(e) => setContact({ instagram: e.target.value || null })} /></Field>
            <Field label={t("website.youtube")}><Input value={c.contact?.youtube ?? ""} onChange={(e) => setContact({ youtube: e.target.value || null })} /></Field>
            <Field label={t("website.mapUrl")}><Input value={c.contact?.map_url ?? ""} onChange={(e) => setContact({ map_url: e.target.value || null })} /></Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>{t("website.theme")}</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-6">
            {(["primary", "accent"] as const).map((k) => (
              <label key={k} className="flex items-center gap-3 text-sm font-medium">
                <input
                  type="color"
                  value={c.theme?.[k] ?? "#1f4e79"}
                  onChange={(e) => set({ theme: { ...c.theme, [k]: e.target.value } })}
                  className="h-10 w-14 cursor-pointer rounded border border-border"
                />
                {t(`website.${k}`)}
              </label>
            ))}
          </CardContent>
        </Card>

        <div className="sticky bottom-0 border-t border-border bg-background/95 py-3 backdrop-blur">
          <Button onClick={save} disabled={busy} size="lg">
            {busy ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      </div>
    </>
  );
}
