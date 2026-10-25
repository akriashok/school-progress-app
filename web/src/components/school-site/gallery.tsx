"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { t } from "@/i18n";

type Item = { src: string; caption?: string };

/** Photo grid with a simple keyboard-accessible lightbox. */
export function Gallery({ items }: { items: Item[] }) {
  const [index, setIndex] = React.useState<number | null>(null);
  const close = () => setIndex(null);
  const step = (d: number) => setIndex((i) => (i === null ? i : (i + d + items.length) % items.length));

  React.useEffect(() => {
    if (index === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") step(1);
      if (e.key === "ArrowLeft") step(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  return (
    <>
      <div className="mt-12 grid grid-cols-2 gap-4 md:grid-cols-3">
        {items.map((it, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setIndex(i)}
            className="group relative aspect-[3/2] overflow-hidden rounded-2xl shadow-md"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={it.src} alt={it.caption || ""} loading="lazy" className="h-full w-full object-cover transition duration-300 group-hover:scale-105" />
            {it.caption ? (
              <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3 text-left text-sm font-medium text-white">
                {it.caption}
              </span>
            ) : null}
          </button>
        ))}
      </div>
      {index !== null ? (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4" onClick={close}>
          <button type="button" aria-label={t("common.close")} className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white" onClick={close}>
            <X className="h-6 w-6" />
          </button>
          {items.length > 1 ? (
            <button type="button" aria-label={t("common.previous")} className="absolute left-3 rounded-full bg-white/10 p-2 text-white" onClick={(e) => { e.stopPropagation(); step(-1); }}>
              <ChevronLeft className="h-7 w-7" />
            </button>
          ) : null}
          <figure className="max-h-full max-w-4xl" onClick={(e) => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={items[index].src} alt={items[index].caption || ""} className="max-h-[80vh] rounded-xl object-contain" />
            {items[index].caption ? <figcaption className="mt-3 text-center text-white">{items[index].caption}</figcaption> : null}
          </figure>
          {items.length > 1 ? (
            <button type="button" aria-label={t("common.next")} className="absolute right-3 rounded-full bg-white/10 p-2 text-white" onClick={(e) => { e.stopPropagation(); step(1); }}>
              <ChevronRight className="h-7 w-7" />
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
