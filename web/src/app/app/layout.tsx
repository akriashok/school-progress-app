"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu, UserRound, X } from "lucide-react";
import { t, type MessageKey } from "@/i18n";
import { useAuth, type Role } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/public-shell";
import { Spinner } from "@/components/ui/misc";

type NavItem = { href: string; label: MessageKey };
type NavGroup = { title?: MessageKey; items: NavItem[] };

const setupItems: NavItem[] = [
  { href: "/app/admin/years", label: "nav.academicYears" },
  { href: "/app/admin/classes", label: "nav.classes" },
  { href: "/app/admin/subjects", label: "nav.subjects" },
  { href: "/app/admin/sections", label: "nav.sections" },
  { href: "/app/admin/teachers", label: "nav.teachers" },
  { href: "/app/admin/assignments", label: "nav.assignments" },
  { href: "/app/admin/students", label: "nav.students" },
  { href: "/app/admin/parents", label: "nav.parents" },
  { href: "/app/admin/imports", label: "nav.imports" },
  { href: "/app/admin/exams", label: "nav.exams" },
  { href: "/app/admin/grade-scales", label: "nav.gradeScales" },
  { href: "/app/admin/school", label: "nav.schoolProfile" },
  { href: "/app/admin/website", label: "nav.website" },
];

function navFor(role: Role): NavGroup[] {
  switch (role) {
    case "PLATFORM_ADMIN":
      return [{ items: [{ href: "/app/platform", label: "nav.schools" }] }];
    case "SCHOOL_ADMIN":
      return [
        {
          items: [
            { href: "/app/admin", label: "nav.overview" },
            { href: "/app/principal", label: "nav.dashboard" },
            { href: "/app/principal/exams", label: "nav.results" },
          ],
        },
        { title: "nav.setup", items: setupItems },
      ];
    case "PRINCIPAL":
      return [
        {
          items: [
            { href: "/app/principal", label: "nav.dashboard" },
            { href: "/app/principal/exams", label: "nav.results" },
            { href: "/app/admin/students", label: "nav.students" },
            { href: "/app/admin/teachers", label: "nav.teachers" },
          ],
        },
      ];
    case "TEACHER":
      return [{ items: [{ href: "/app/teacher", label: "nav.myClasses" }] }];
    default:
      return [{ items: [{ href: "/app/family", label: role === "PARENT" ? "nav.children" : "nav.results" }] }];
  }
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/app/admin" || href === "/app/principal") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
    if (auth.status === "authenticated" && auth.me.consent_required) router.replace("/consent");
  }, [auth, router]);

  React.useEffect(() => setOpen(false), [pathname]);

  if (auth.status !== "authenticated" || auth.me.consent_required) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }
  const me = auth.me;
  const groups = navFor(me.role);

  const nav = (
    <nav className="flex flex-col gap-5" aria-label={t("nav.menu")}>
      {groups.map((g, i) => (
        <div key={i} className="flex flex-col gap-0.5">
          {g.title ? (
            <div className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t(g.title)}
            </div>
          ) : null}
          {g.items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-md px-3 py-2 text-sm transition-colors hover:bg-muted",
                isActive(pathname, item.href) && "bg-secondary font-medium text-secondary-foreground",
              )}
            >
              {t(item.label)}
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-card/95 backdrop-blur">
        <div className="flex h-14 items-center justify-between gap-3 px-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-md p-2 hover:bg-muted lg:hidden"
              aria-label={t("nav.menu")}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <Logo />
            {me.school_name ? (
              <span className="hidden truncate text-sm text-muted-foreground md:inline">· {me.school_name}</span>
            ) : null}
          </div>
          <div className="flex items-center gap-1">
            <Link
              href="/app/profile"
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
              title={t("nav.profile")}
            >
              <UserRound className="h-4 w-4" aria-hidden />
              <span className="hidden max-w-40 truncate sm:inline">{me.full_name}</span>
              <span className="hidden text-xs text-muted-foreground sm:inline">({t(`roles.${me.role}`)})</span>
            </Link>
            <button
              type="button"
              onClick={() => auth.logout().then(() => router.replace("/login"))}
              className="rounded-md p-2 hover:bg-muted"
              title={t("nav.logout")}
              aria-label={t("nav.logout")}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>
      <div className="flex">
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-60 shrink-0 overflow-y-auto border-r border-border bg-card p-3 lg:block">
          {nav}
        </aside>
        {open ? (
          <div className="fixed inset-0 top-14 z-20 overflow-y-auto bg-card p-4 lg:hidden">{nav}</div>
        ) : null}
        <main className="min-w-0 flex-1 px-4 py-6 md:px-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
