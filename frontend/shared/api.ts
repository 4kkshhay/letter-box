/** Client for the page API. The page's key is the last segment of its URL. */

export type FieldDef =
  | { type: "enum"; options: string[] }
  | { type: "multi"; options: string[] }
  | { type: "string"; max_length: number };

export type FieldValue = string | string[];

export interface PageData {
  title: string;
  acknowledgement: boolean;
  fields: Record<string, FieldDef>;
  state: Record<string, FieldValue>;
  acknowledged: boolean;
}

/** The link no longer leads to a page. */
export class PageUnavailableError extends Error {}

/** `/l/<slug>` → `/api/v1/pages/<slug>` */
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
