import type { Metadata } from "next";
import { t } from "@/i18n";
import { PublicShell } from "@/components/public-shell";

export const metadata: Metadata = { title: t("legal.termsTitle") };

// Draft text for the pilot. Must be reviewed by a lawyer before production.
export default function TermsPage() {
  return (
    <PublicShell>
      <article className="mx-auto max-w-3xl space-y-4 px-4 py-12 leading-relaxed">
        <h1 className="text-3xl font-semibold">{t("legal.termsTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("legal.updated")}</p>
        <p>
          VidyaTrack is provided to schools under a written agreement. Parents, students and staff use it through
          their school. By logging in you agree to use the app only for its purpose: viewing and managing academic
          results for your school or your own children.
        </p>
        <ul className="list-disc space-y-1 pl-6">
          <li>Keep your OTP and PIN private. Do not share your login.</li>
          <li>Marks shown are entered by the school. Contact the school if something looks wrong.</li>
          <li>Do not try to access another person&apos;s data. All access is logged.</li>
          <li>The school can disable accounts, for example when a student leaves.</li>
        </ul>
      </article>
    </PublicShell>
  );
}
