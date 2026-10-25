import type { Metadata } from "next";
import { t } from "@/i18n";
import { ProductLanding } from "@/components/landing/product-landing";
import { SchoolSite } from "@/components/school-site/school-site";
import { loadSite } from "@/components/school-site/load";

// Single-school deployments set HOME_SCHOOL_CODE so "/" shows that school's website;
// otherwise "/" is the VidyaTrack product page.
const HOME_SCHOOL_CODE = process.env.HOME_SCHOOL_CODE;

export const revalidate = 60;

export async function generateMetadata(): Promise<Metadata> {
  const site = HOME_SCHOOL_CODE ? await loadSite(HOME_SCHOOL_CODE) : null;
  return site ? { title: { absolute: site.name } } : { title: { absolute: `${t("brand.name")} · ${t("brand.tagline")}` } };
}

export default async function Home() {
  const site = HOME_SCHOOL_CODE ? await loadSite(HOME_SCHOOL_CODE) : null;
  return site ? <SchoolSite site={site} /> : <ProductLanding />;
}
