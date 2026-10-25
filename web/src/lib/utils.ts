import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

function toNumber(v: string | number): number {
  return typeof v === "string" ? parseFloat(v) : v;
}

export function num(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "–";
  const n = toNumber(v);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

export function pct(v: string | number | null | undefined): string {
  const s = num(v);
  return s === "–" ? s : `${s}%`;
}

export function asNumber(v: string | number | null | undefined): number | null {
  if (v === null || v === undefined || v === "") return null;
  return toNumber(v);
}
