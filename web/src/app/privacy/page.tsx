import type { Metadata } from "next";
import { t } from "@/i18n";
import { PublicShell } from "@/components/public-shell";

export const metadata: Metadata = { title: t("legal.privacyTitle") };

// Draft text for the pilot. Must be reviewed by a lawyer before production (DPDP Act 2023).
export default function PrivacyPage() {
  return (
    <PublicShell>
      <article className="mx-auto max-w-3xl space-y-4 px-4 py-12 leading-relaxed">
        <h1 className="text-3xl font-semibold">{t("legal.privacyTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("legal.updated")}</p>
        <h2 className="pt-4 text-xl font-semibold">Who we are</h2>
        <p>
          VidyaTrack provides software to schools. Each school decides what student data is entered and who can see
          it. For personal data in the app, the school is the Data Fiduciary and VidyaTrack is its Data Processor.
        </p>
        <h2 className="pt-4 text-xl font-semibold">What we store</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>Students: name, admission number, roll number, class and section, date of birth, gender, marks.</li>
          <li>Parents and staff: name and mobile number, used for one-time password login.</li>
          <li>Records of logins, marks changes and consent, kept for security and audit.</li>
        </ul>
        <h2 className="pt-4 text-xl font-semibold">How we use it</h2>
        <p>
          Only to show marks, report cards and progress to the school, the student and their linked parents. We do not
          show ads, we do not use third-party trackers or analytics, and we never sell data.
        </p>
        <h2 className="pt-4 text-xl font-semibold">Where it is kept</h2>
        <p>All data is stored on servers in India, encrypted at rest and in transit, with daily backups.</p>
        <h2 className="pt-4 text-xl font-semibold">Your choices</h2>
        <p>
          Parents give consent the first time they log in. You can ask your school to correct or delete your data, or
          to export it. When a school stops using VidyaTrack, its data is exported to the school and deleted.
        </p>
        <h2 className="pt-4 text-xl font-semibold">Contact</h2>
        <p>For questions about your child&apos;s data, contact your school office first.</p>
      </article>
    </PublicShell>
  );
}
