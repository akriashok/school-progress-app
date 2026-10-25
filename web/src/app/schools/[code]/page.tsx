import type { Metadata } from "next";
import { t } from "@/i18n";
import { PublicShell } from "@/components/public-shell";
import { SchoolSite } from "@/components/school-site/school-site";
import { loadSite } from "@/components/school-site/load";

type Props = { params: Promise<{ code: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const site = await loadSite((await params).code);
  if (!site) return { title: t("school.notFound") };
  return { title: { absolute: site.name }, description: site.website.hero_subtitle || site.website.tagline };
}

export default async function SchoolPage({ params }: Props) {
  const site = await loadSite((await params).code);
  if (!site) {
    return (
      <PublicShell>
        <p className="mx-auto max-w-3xl px-4 py-24 text-center text-muted-foreground">{t("school.notFound")}</p>
      </PublicShell>
    );
  }
  return <SchoolSite site={site} />;
}
