"use client";

import * as React from "react";
import { ApiError } from "./api";
import { t, type MessageKey } from "@/i18n";

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const key = `errors.${err.code}` as MessageKey;
    const translated = t(key);
    return translated === key ? err.message : translated;
  }
  if (err instanceof TypeError) return t("errors.network");
  return t("common.error");
}

/** Minimal data loader: runs `fn` when deps change; exposes reload(). */
export function useQuery<T>(fn: () => Promise<T>, deps: React.DependencyList, enabled = true) {
  const [data, setData] = React.useState<T | undefined>(undefined);
  const [error, setError] = React.useState<unknown>(null);
  const [loading, setLoading] = React.useState<boolean>(enabled);
  const [tick, setTick] = React.useState(0);
  const fnRef = React.useRef(fn);
  fnRef.current = fn;

  React.useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fnRef
      .current()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, enabled]);

  const reload = React.useCallback(() => setTick((x) => x + 1), []);
  return { data, error, loading, reload, setData };
}

/** Wrap an async action with busy + error state. */
export function useAction() {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const run = React.useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(errorMessage(e));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, setError, run };
}
