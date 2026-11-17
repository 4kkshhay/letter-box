import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPage, pageApiUrl, PageUnavailableError } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("pageApiUrl", () => {
  it("uses the last path segment as the page key", () => {
    expect(pageApiUrl("/l/abc-DEF_123")).toBe("/api/v1/pages/abc-DEF_123");
    expect(pageApiUrl("/view/demo-static")).toBe("/api/v1/pages/demo-static");
    expect(pageApiUrl("/l/abc/")).toBe("/api/v1/pages/abc");
  });
});

describe("fetchPage", () => {
  const stubFetch = (response: Partial<Response>) => {
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  };

  it("requests the page uncached and returns its data", async () => {
    const data = { title: "T", acknowledgement: false, fields: {}, state: {}, acknowledged: false };
    const fetchMock = stubFetch({ ok: true, status: 200, json: () => Promise.resolve(data) });
    window.history.replaceState(null, "", "/l/some-slug");

    await expect(fetchPage()).resolves.toEqual(data);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/pages/some-slug",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("reports a missing page distinctly", async () => {
    stubFetch({ ok: false, status: 404 });
    await expect(fetchPage()).rejects.toBeInstanceOf(PageUnavailableError);
  });

  it("treats other failures as generic errors", async () => {
    stubFetch({ ok: false, status: 500 });
    const failure = await fetchPage().catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(Error);
    expect(failure).not.toBeInstanceOf(PageUnavailableError);
  });
});
