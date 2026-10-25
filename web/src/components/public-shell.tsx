import Link from "next/link";
import { GraduationCap } from "lucide-react";
import { t } from "@/i18n";
import { Button } from "@/components/ui/button";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold text-primary">
      <GraduationCap className="h-6 w-6" aria-hidden />
      <span className="text-lg tracking-tight">{t("brand.name")}</span>
    </Link>
  );
}

export function PublicHeader() {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Logo />
        <nav className="flex items-center gap-2">
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link href="/#demo">{t("landing.ctaDemo")}</Link>
          </Button>
          <Button asChild>
            <Link href="/login">{t("nav.login")}</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p>{t("landing.footerRights")}</p>
        <nav className="flex gap-4">
          <Link href="/privacy" className="hover:text-foreground">
            {t("landing.footerPrivacy")}
          </Link>
          <Link href="/terms" className="hover:text-foreground">
            {t("landing.footerTerms")}
          </Link>
        </nav>
      </div>
    </footer>
  );
}

export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />
      <main className="flex-1">{children}</main>
      <PublicFooter />
    </div>
  );
}
