import type { Schemas } from "@/lib/api";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/** Server-side fetch of a school's public website content (cached briefly). */
export async function loadSite(code: string): Promise<Schemas["PublicWebsite"] | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/public/schools/${encodeURIComponent(code)}/website`, {
      next: { revalidate: 60 },
    });
    return res.ok ? ((await res.json()) as Schemas["PublicWebsite"]) : null;
  } catch {
    return null;
  }
}
