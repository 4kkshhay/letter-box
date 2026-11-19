/** Client for the page API. The page's key is the last segment of its URL. */

export type FieldDef =
  | { type: "enum"; options: string[] }
  | { type: "multi"; options: string[] }
  | { type: "string"; max_length: number };

export type FieldValue = string | string[];

/** A partial update; `null` removes a saved value. */
export type FieldUpdate = Record<string, FieldValue | null>;

export interface PageData {
  title: string;
  fields: Record<string, FieldDef>;
  state: Record<string, FieldValue>;
  /** Present only on the authenticated, read-only admin preview. */
  admin?: true;
}

/** The link no longer leads to a page. */
export class PageUnavailableError extends Error {}

/**
 * Why an action did not succeed: the server rejected the input, the page is
 * gone, or the request failed or never arrived.
 */
export type FailureKind = "invalid" | "unavailable" | "failed";

export class ActionError extends Error {
  constructor(readonly kind: FailureKind) {
    super(`Action failed: ${kind}`);
  }
}

/** `/<slug>` → `/api/v1/pages/<slug>` */
export function pageApiUrl(pathname: string = window.location.pathname): string {
  const key = pathname.split("/").filter(Boolean).at(-1) ?? "";
  return `/api/v1/pages/${encodeURIComponent(key)}`;
}

export async function fetchPage(signal?: AbortSignal): Promise<PageData> {
  const response = await fetch(pageApiUrl(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
    signal,
  });
  if (response.status === 404) {
    throw new PageUnavailableError();
  }
  if (!response.ok) {
    throw new Error(`Unexpected response: ${response.status}`);
  }
  return (await response.json()) as PageData;
}

async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${pageApiUrl()}${path}`, {
      cache: "no-store",
      ...init,
      headers: { Accept: "application/json", ...init.headers },
    });
  } catch {
    throw new ActionError("failed");
  }
  if (response.status === 404) {
    throw new ActionError("unavailable");
  }
  if (response.status === 422) {
    throw new ActionError("invalid");
  }
  if (!response.ok) {
    throw new ActionError("failed");
  }
  return response;
}

/**
 * Saves the given fields and returns all saved values afterwards.
 * `keepalive` lets a save started as the page closes still complete.
 */
/** The visitor's IANA timezone, so the admin sees times as the visitor did. */
export function visitorTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

function query(params: Record<string, string | null>): string {
  const entries = Object.entries(params).filter((entry): entry is [string, string] => !!entry[1]);
  return entries.length ? `?${new URLSearchParams(entries)}` : "";
}

export async function saveFields(fields: FieldUpdate): Promise<Record<string, FieldValue>> {
  const response = await send(`/state${query({ tz: visitorTimezone() })}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
    keepalive: true,
  });
  let body: { state?: Record<string, FieldValue>; saved?: boolean };
  try {
    body = (await response.json()) as typeof body;
  } catch {
    throw new ActionError("failed");
  }
  if (body.saved !== true || !body.state) {
    throw new ActionError("failed");
  }
  return body.state;
}

const OPEN_KINDS = new Set(["navigate", "reload", "back_forward"]);

/** How the browser loaded this document, if it is one the server records. */
export function navigationKind(): string | null {
  const entry = performance.getEntriesByType?.("navigation")[0] as
    | PerformanceNavigationTiming
    | undefined;
  return entry && OPEN_KINDS.has(entry.type) ? entry.type : null;
}

/**
 * Reports one open of this page with how it was loaded, so the admin can tell
 * refreshes from new opens; the first one is shown as "received". `keepalive`
 * lets it finish if the page is closed.
 */
export async function recordOpen(): Promise<void> {
  const params = query({ kind: navigationKind(), tz: visitorTimezone() });
  await send(`/open${params}`, { method: "POST", keepalive: true });
}
