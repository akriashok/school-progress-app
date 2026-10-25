import { en } from "./en";

// v1 ships English only; Telugu/Hindi dictionaries plug in here later (same keys).
type Dict = typeof en;

type Paths<T, P extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${P}${K}` : Paths<T[K], `${P}${K}.`>;
}[keyof T & string];

export type MessageKey = Paths<Dict>;

export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  let node: unknown = en;
  for (const part of key.split(".")) {
    node = (node as Record<string, unknown>)[part];
  }
  let text = typeof node === "string" ? node : key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, String(v));
  }
  return text;
}
