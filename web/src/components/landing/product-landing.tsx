import Link from "next/link";
import { BarChart3, FileSpreadsheet, ShieldCheck, Smartphone } from "lucide-react";
import { t } from "@/i18n";
import { PublicShell } from "@/components/public-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoForm } from "@/components/demo-form";

const features = [
  { icon: FileSpreadsheet, title: t("landing.f1Title"), body: t("landing.f1Body") },
  { icon: BarChart3, title: t("landing.f2Title"), body: t("landing.f2Body") },
  { icon: Smartphone, title: t("landing.f3Title"), body: t("landing.f3Body") },
  { icon: ShieldCheck, title: t("landing.f4Title"), body: t("landing.f4Body") },
];

function DashboardPreview() {
  // A static, data-free illustration of the principal dashboard (no screenshots of real data).
  const bars = [62, 71, 58, 77, 66, 54];
  return (
    <div aria-hidden className="rounded-xl border border-border bg-card p-5 shadow-lg">
      <div className="mb-4 grid grid-cols-3 gap-3">
        {["Average", "Pass rate", "Published"].map((l, i) => (
          <div key={l} className="rounded-md bg-muted p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{l}</div>
            <div className="text-xl font-semibold">{["64.2%", "91%", "6/6"][i]}</div>
          </div>
        ))}
      </div>
      <div className="flex h-36 items-end gap-3 border-b border-border px-2">
        {bars.map((h, i) => (
          <div key={i} className="flex-1 rounded-t bg-primary/80" style={{ height: `${h}%` }} />
        ))}
      </div>
      <div className="mt-2 flex justify-between px-2 text-[11px] text-muted-foreground">
        {["6-A", "6-B", "7-A", "7-B", "8-A", "8-B"].map((s) => (
          <span key={s}>{s}</span>
        ))}
      </div>
    </div>
  );
}

export function ProductLanding() {
  return (
    <PublicShell>
      <section className="bg-gradient-to-b from-secondary/60 to-background">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 md:grid-cols-2 md:py-24">
          <div>
            <h1 className="text-3xl font-bold leading-tight tracking-tight md:text-5xl">{t("landing.heroTitle")}</h1>
            <p className="mt-5 text-lg text-muted-foreground">{t("landing.heroBody")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="#demo">{t("landing.ctaDemo")}</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/login">{t("landing.ctaLogin")}</Link>
              </Button>
            </div>
          </div>
          <DashboardPreview />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">{t("landing.featuresTitle")}</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, body }) => (
            <Card key={title}>
              <CardHeader>
                <Icon className="h-6 w-6 text-primary" aria-hidden />
                <CardTitle className="mt-2">{title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{body}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-border bg-card">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold tracking-tight">{t("landing.howTitle")}</h2>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            {[t("landing.how1"), t("landing.how2"), t("landing.how3")].map((step, i) => (
              <li key={step} className="flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground">
                  {i + 1}
                </span>
                <p className="pt-1.5">{step}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-2xl font-semibold tracking-tight">{t("landing.pricingTitle")}</h2>
        <p className="mt-2 text-muted-foreground">{t("landing.pricingBody")}</p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {[
            [t("landing.pricingStarter"), t("landing.pricingStarterPrice"), t("landing.pricingStarterBody")],
            [t("landing.pricingStandard"), t("landing.pricingStandardPrice"), t("landing.pricingStandardBody")],
          ].map(([name, price, body]) => (
            <Card key={name}>
              <CardHeader>
                <CardTitle>{name}</CardTitle>
                <p className="text-2xl font-semibold text-primary">{price}</p>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{body}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section id="demo" className="border-t border-border bg-card">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 md:grid-cols-2">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">{t("landing.demoTitle")}</h2>
            <p className="mt-2 text-muted-foreground">{t("landing.demoBody")}</p>
          </div>
          <DemoForm />
        </div>
      </section>
    </PublicShell>
  );
}
