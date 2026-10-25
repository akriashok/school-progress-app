import Link from "next/link";
import {
  BookOpen,
  Bus,
  CheckCircle2,
  Clock,
  FlaskConical,
  Heart,
  Mail,
  MapPin,
  Monitor,
  Music,
  Palette,
  Phone,
  ShieldCheck,
  Sparkles,
  Trees,
  Trophy,
  type LucideIcon,
} from "lucide-react";
import type { Schemas } from "@/lib/api";
import { t } from "@/i18n";
import { Gallery } from "./gallery";
import { SiteNav } from "./site-nav";
import { Clouds, SocialIcon, WhatsAppIcon } from "./art";

type Site = Schemas["PublicWebsite"];

const ICONS: Record<string, LucideIcon> = {
  bus: Bus,
  music: Music,
  playground: Trees,
  book: BookOpen,
  computer: Monitor,
  heart: Heart,
  trophy: Trophy,
  flask: FlaskConical,
  palette: Palette,
  shield: ShieldCheck,
};

export function imageUrl(code: string, id: string) {
  return `/api/v1/public/schools/${code}/images/${id}`;
}

function Photo({ code, id, alt, className, icon: Icon = Sparkles }: {
  code: string;
  id?: string | null;
  alt: string;
  className?: string;
  icon?: LucideIcon;
}) {
  if (id) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={imageUrl(code, id)} alt={alt} loading="lazy" className={`object-cover ${className ?? ""}`} />;
  }
  return (
    <div
      aria-hidden
      className={`flex items-center justify-center bg-gradient-to-br from-[var(--site-primary)]/15 via-[var(--site-accent)]/15 to-[var(--site-primary)]/5 ${className ?? ""}`}
    >
      <Icon className="h-12 w-12 text-[var(--site-primary)]/60" />
    </div>
  );
}

function SectionTitle({ eyebrow, title, center = true }: { eyebrow: string; title: string; center?: boolean }) {
  return (
    <div className={center ? "mx-auto max-w-2xl text-center" : ""}>
      <p className="font-semibold uppercase tracking-[0.2em] text-[var(--site-accent)] text-xs">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
    </div>
  );
}

export function SchoolSite({ site }: { site: Site }) {
  const w = site.website;
  const code = site.code;
  const address = [site.address, site.city, site.state, site.pincode].filter(Boolean).join(", ");
  const whatsapp = w.contact.whatsapp ? `https://wa.me/${w.contact.whatsapp.replace(/\D/g, "")}` : null;
  const socials = (["facebook", "instagram", "youtube"] as const).filter((k) => w.contact[k]);
  const style = { "--site-primary": w.theme.primary, "--site-accent": w.theme.accent } as React.CSSProperties;

  const nav = [
    { href: "#about", label: t("site.navAbout") },
    ...(w.facilities.length ? [{ href: "#facilities", label: t("site.navFacilities") }] : []),
    ...(w.gallery.length ? [{ href: "#gallery", label: t("site.navGallery") }] : []),
    ...(w.leaders.length ? [{ href: "#leadership", label: t("site.navLeadership") }] : []),
    ...(w.admissions.open ? [{ href: "#admissions", label: t("site.navAdmissions") }] : []),
    { href: "#contact", label: t("site.navContact") },
  ];

  return (
    <div style={style} className="bg-white text-slate-900 [color-scheme:light]">
      {/* Top bar */}
      <div className="bg-[var(--site-primary)] text-white/90 text-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-2">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
            {site.phone ? (
              <a href={`tel:${site.phone}`} className="flex items-center gap-1.5 hover:text-white">
                <Phone className="h-3.5 w-3.5" aria-hidden /> {site.phone}
              </a>
            ) : null}
            {site.email ? (
              <a href={`mailto:${site.email}`} className="hidden items-center gap-1.5 hover:text-white sm:flex">
                <Mail className="h-3.5 w-3.5" aria-hidden /> {site.email}
              </a>
            ) : null}
            {w.contact.timings ? (
              <span className="hidden items-center gap-1.5 md:flex">
                <Clock className="h-3.5 w-3.5" aria-hidden /> {w.contact.timings}
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            {socials.map((k) => (
              <a key={k} href={w.contact[k] ?? "#"} target="_blank" rel="noopener noreferrer" aria-label={k} className="hover:text-white">
                <SocialIcon name={k} className="h-4 w-4" />
              </a>
            ))}
          </div>
        </div>
      </div>

      <SiteNav name={site.name} code={code} hasLogo={site.has_logo} items={nav} />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-sky-50 via-white to-white">
        <Clouds className="pointer-events-none absolute inset-x-0 top-0 h-full w-full text-sky-100" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 md:grid-cols-2 md:py-20">
          <div>
            {w.tagline ? (
              <span className="inline-flex items-center gap-2 rounded-full bg-[var(--site-accent)]/15 px-4 py-1.5 text-sm font-semibold text-[var(--site-primary)]">
                <Sparkles className="h-4 w-4 text-[var(--site-accent)]" aria-hidden /> {w.tagline}
              </span>
            ) : null}
            <h1 className="mt-5 text-4xl font-extrabold leading-tight tracking-tight md:text-6xl">
              {w.hero_title || site.name}
            </h1>
            {w.hero_subtitle ? <p className="mt-5 text-lg leading-relaxed text-slate-600">{w.hero_subtitle}</p> : null}
            <div className="mt-8 flex flex-wrap gap-3">
              {w.admissions.open ? (
                <a href="#admissions" className="rounded-full bg-[var(--site-accent)] px-6 py-3 font-semibold text-white shadow-lg shadow-[var(--site-accent)]/30 transition hover:brightness-110">
                  {t("site.admissionsCta")}
                </a>
              ) : null}
              <Link href="/login" className="rounded-full border-2 border-[var(--site-primary)] px-6 py-3 font-semibold text-[var(--site-primary)] transition hover:bg-[var(--site-primary)] hover:text-white">
                {t("site.parentLogin")}
              </Link>
            </div>
          </div>
          <div className="relative">
            <div className="absolute -left-4 -top-4 h-24 w-24 rounded-full bg-[var(--site-accent)]/30 blur-xl" aria-hidden />
            <div className="absolute -bottom-6 -right-4 h-32 w-32 rounded-full bg-[var(--site-primary)]/20 blur-xl" aria-hidden />
            <Photo
              code={code}
              id={w.hero_image}
              alt={site.name}
              icon={BookOpen}
              className="relative aspect-[4/3] w-full rounded-[2rem] border-8 border-white shadow-2xl"
            />
          </div>
        </div>
      </section>

      {/* Highlights */}
      {w.highlights.length ? (
        <section className="mx-auto max-w-6xl px-4 py-16">
          <div className={`grid gap-6 sm:grid-cols-2 ${w.highlights.length >= 4 ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}>
            {w.highlights.map((h, i) => (
              <article key={i} className="group overflow-hidden rounded-3xl bg-white shadow-md ring-1 ring-slate-100 transition hover:-translate-y-1 hover:shadow-xl">
                <Photo code={code} id={h.image} alt={h.title} className="aspect-[16/10] w-full" />
                <div className="p-6">
                  <div className="mb-3 h-1.5 w-12 rounded-full bg-[var(--site-accent)]" aria-hidden />
                  <h3 className="text-xl font-bold">{h.title}</h3>
                  {h.body ? <p className="mt-2 text-slate-600">{h.body}</p> : null}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {/* About */}
      <section id="about" className="scroll-mt-20 bg-amber-50/60">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 md:grid-cols-2">
          <Photo code={code} id={w.about_image} alt={w.about_title || site.name} icon={Heart} className="aspect-square w-full rounded-[2rem] shadow-xl" />
          <div>
            <SectionTitle eyebrow={t("site.aboutEyebrow")} title={w.about_title || site.name} center={false} />
            {w.about_body ? <p className="mt-5 whitespace-pre-line text-lg leading-relaxed text-slate-700">{w.about_body}</p> : null}
            {w.excellence.length ? (
              <ul className="mt-6 grid gap-3 sm:grid-cols-2">
                {w.excellence.map((e, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[var(--site-accent)]" aria-hidden />
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      </section>

      {/* Stats */}
      {w.stats.length ? (
        <section className="bg-[var(--site-primary)] text-white">
          <div className={`mx-auto grid max-w-6xl gap-8 px-4 py-14 text-center grid-cols-2 ${w.stats.length >= 4 ? "md:grid-cols-4" : "md:grid-cols-3"}`}>
            {w.stats.map((s, i) => (
              <div key={i}>
                <div className="text-4xl font-extrabold md:text-5xl">{s.value}</div>
                <div className="mt-1 text-sm font-medium uppercase tracking-wider text-white/80">{s.label}</div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* Facilities */}
      {w.facilities.length ? (
        <section id="facilities" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20">
          <SectionTitle eyebrow={t("site.facilitiesEyebrow")} title={t("site.facilitiesTitle")} />
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {w.facilities.map((f, i) => {
              const Icon = ICONS[f.icon] ?? BookOpen;
              return (
                <article key={i} className="overflow-hidden rounded-3xl bg-white shadow-md ring-1 ring-slate-100">
                  {f.image ? <Photo code={code} id={f.image} alt={f.title} className="aspect-[16/10] w-full" /> : null}
                  <div className="p-6">
                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--site-primary)]/10 text-[var(--site-primary)]">
                      <Icon className="h-6 w-6" aria-hidden />
                    </span>
                    <h3 className="mt-4 text-lg font-bold">{f.title}</h3>
                    {f.body ? <p className="mt-1.5 text-slate-600">{f.body}</p> : null}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      {/* Gallery */}
      {w.gallery.length ? (
        <section id="gallery" className="scroll-mt-20 bg-sky-50/70">
          <div className="mx-auto max-w-6xl px-4 py-20">
            <SectionTitle eyebrow={t("site.galleryEyebrow")} title={t("site.galleryTitle")} />
            <Gallery items={w.gallery.map((g) => ({ src: imageUrl(code, g.image), caption: g.caption }))} />
          </div>
        </section>
      ) : null}

      {/* Leadership */}
      {w.leaders.length ? (
        <section id="leadership" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20">
          <SectionTitle eyebrow={t("site.leadershipEyebrow")} title={t("site.leadershipTitle")} />
          <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {w.leaders.map((l, i) => (
              <article key={i} className="rounded-3xl bg-white p-6 text-center shadow-md ring-1 ring-slate-100">
                <Photo code={code} id={l.photo} alt={l.name} icon={Heart} className="mx-auto h-32 w-32 rounded-full ring-4 ring-[var(--site-accent)]/40" />
                <h3 className="mt-4 text-xl font-bold">{l.name}</h3>
                {l.role ? <p className="font-medium text-[var(--site-primary)]">{l.role}</p> : null}
                {l.bio ? <p className="mt-3 text-slate-600">{l.bio}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {/* Admissions */}
      {w.admissions.open ? (
        <section id="admissions" className="scroll-mt-20 px-4 pb-20">
          <div className="relative mx-auto max-w-6xl overflow-hidden rounded-[2rem] bg-gradient-to-r from-[var(--site-primary)] to-[var(--site-primary)]/80 px-8 py-12 text-white md:px-14">
            <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-[var(--site-accent)]/40" aria-hidden />
            <div className="relative max-w-2xl">
              <h2 className="text-3xl font-bold md:text-4xl">{w.admissions.title || t("site.admissionsCta")}</h2>
              {w.admissions.body ? <p className="mt-3 text-lg text-white/90">{w.admissions.body}</p> : null}
              <div className="mt-6 flex flex-wrap gap-3">
                {whatsapp ? (
                  <a href={whatsapp} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 font-semibold text-[var(--site-primary)] hover:bg-white/90">
                    <WhatsAppIcon className="h-5 w-5" /> {t("site.whatsapp")}
                  </a>
                ) : null}
                {site.phone ? (
                  <a href={`tel:${site.phone}`} className="inline-flex items-center gap-2 rounded-full border-2 border-white px-6 py-3 font-semibold hover:bg-white/10">
                    <Phone className="h-5 w-5" aria-hidden /> {t("site.call")}
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* Footer / contact */}
      <footer id="contact" className="scroll-mt-20 bg-slate-900 text-slate-300">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 md:grid-cols-3">
          <div>
            <div className="flex items-center gap-3">
              {site.has_logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={`/api/v1/public/schools/${code}/logo`} alt="" className="h-12 w-12 rounded-lg bg-white object-contain p-1" />
              ) : null}
              <span className="text-xl font-bold text-white">{site.name}</span>
            </div>
            {w.tagline ? <p className="mt-3 text-sm">{w.tagline}</p> : null}
            <div className="mt-5 flex gap-3">
              {socials.map((k) => (
                <a key={k} href={w.contact[k] ?? "#"} target="_blank" rel="noopener noreferrer" aria-label={k} className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 hover:bg-[var(--site-accent)]">
                  <SocialIcon name={k} className="h-4 w-4 text-white" />
                </a>
              ))}
            </div>
          </div>
          <div>
            <h3 className="font-semibold text-white">{t("site.quickLinks")}</h3>
            <ul className="mt-4 space-y-2 text-sm">
              {nav.map((n) => (
                <li key={n.href}>
                  <a href={n.href} className="hover:text-white">{n.label}</a>
                </li>
              ))}
              <li><Link href="/login" className="hover:text-white">{t("site.parentLogin")}</Link></li>
              <li><Link href={`/login/student?school=${code}`} className="hover:text-white">{t("site.studentLogin")}</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-white">{t("site.reachUs")}</h3>
            <ul className="mt-4 space-y-3 text-sm">
              {address ? (
                <li className="flex gap-2"><MapPin className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {address}</li>
              ) : null}
              {site.phone ? (
                <li className="flex gap-2"><Phone className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> <a href={`tel:${site.phone}`} className="hover:text-white">{site.phone}</a></li>
              ) : null}
              {site.email ? (
                <li className="flex gap-2"><Mail className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> <a href={`mailto:${site.email}`} className="hover:text-white">{site.email}</a></li>
              ) : null}
              {w.contact.map_url ? (
                <li><a href={w.contact.map_url} target="_blank" rel="noopener noreferrer" className="font-medium text-[var(--site-accent)] hover:underline">{t("site.directions")}</a></li>
              ) : null}
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10">
          <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-5 text-xs text-slate-400">
            <span>© {new Date().getFullYear()} {site.name}</span>
            <span>
              <Link href="/privacy" className="hover:text-white">{t("landing.footerPrivacy")}</Link> ·{" "}
              {t("site.poweredBy")}
            </span>
          </div>
        </div>
      </footer>

      {whatsapp ? (
        <a
          href={whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={t("site.whatsapp")}
          className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#25D366] text-white shadow-xl transition hover:scale-105"
        >
          <WhatsAppIcon className="h-7 w-7" />
        </a>
      ) : null}
    </div>
  );
}
