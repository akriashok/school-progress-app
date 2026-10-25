"use client";

import * as React from "react";
import Link from "next/link";
import { GraduationCap, Menu, X } from "lucide-react";
import { t } from "@/i18n";

export function SiteNav({
  name,
  code,
  hasLogo,
  items,
}: {
  name: string;
  code: string;
  hasLogo: boolean;
  items: { href: string; label: string }[];
}) {
  const [open, setOpen] = React.useState(false);
  return (
    <header className="sticky top-0 z-30 border-b border-slate-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <a href="#" className="flex min-w-0 items-center gap-2.5">
          {hasLogo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={`/api/v1/public/schools/${code}/logo`} alt="" className="h-10 w-10 rounded-lg object-contain" />
          ) : (
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--site-primary)] text-white">
              <GraduationCap className="h-6 w-6" aria-hidden />
            </span>
          )}
          <span className="truncate text-lg font-bold text-[var(--site-primary)]">{name}</span>
        </a>
        <nav className="hidden items-center gap-6 text-sm font-medium lg:flex">
          {items.map((i) => (
            <a key={i.href} href={i.href} className="text-slate-700 hover:text-[var(--site-primary)]">
              {i.label}
            </a>
          ))}
          <Link href="/login" className="rounded-full bg-[var(--site-primary)] px-5 py-2 text-white hover:brightness-110">
            {t("site.login")}
          </Link>
        </nav>
        <button
          type="button"
          className="rounded-md p-2 text-slate-700 lg:hidden"
          aria-label={t("nav.menu")}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>
      {open ? (
        <nav className="border-t border-slate-100 bg-white px-4 py-3 lg:hidden">
          {items.map((i) => (
            <a key={i.href} href={i.href} onClick={() => setOpen(false)} className="block py-2.5 font-medium text-slate-700">
              {i.label}
            </a>
          ))}
          <Link href="/login" className="mt-2 block rounded-full bg-[var(--site-primary)] px-5 py-2.5 text-center font-medium text-white">
            {t("site.login")}
          </Link>
        </nav>
      ) : null}
    </header>
  );
}
