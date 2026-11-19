import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ActionError,
  fetchPage,
  pageApiUrl,
  PageUnavailableError,
  recordOpen,
  saveFields,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("pageApiUrl", () => {
  it("uses the last path segment as the page key", () => {
    expect(pageApiUrl("/abc-DEF_123")).toBe("/api/v1/pages/abc-DEF_123");
    expect(pageApiUrl("/view/demo-static")).toBe("/api/v1/pages/demo-static");
    expect(pageApiUrl("/abc/")).toBe("/api/v1/pages/abc");
  });
});

describe("fetchPage", () => {
  const stubFetch = (response: Partial<Response>) => {
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  };

  it("requests the page uncached and returns its data", async () => {
    const data = { title: "T", fields: {}, state: {} };
    const fetchMock = stubFetch({ ok: true, status: 200, json: () => Promise.resolve(data) });
    window.history.replaceState(null, "", "/some-slug");

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

describe("actions", () => {
  const ok = (body?: unknown): Partial<Response> => ({
    ok: true,
    status: body === undefined ? 204 : 200,
    json: () => Promise.resolve(body),
  });

  const failureKind = (promise: Promise<unknown>) =>
    promise.then(
      () => "resolved",
      (error: unknown) => (error instanceof ActionError ? error.kind : "other"),
    );

  const setTimezone = (timeZone: string | undefined) =>
    vi
      .spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions")
      .mockReturnValue({ timeZone } as Intl.ResolvedDateTimeFormatOptions);

  it("saveFields sends a JSON PATCH and returns the saved state", async () => {
    window.history.replaceState(null, "", "/some-slug");
    setTimezone("Europe/London");
    const fetchMock = vi.fn().mockResolvedValue(ok({ state: { choice: "b" }, saved: true }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(saveFields({ choice: "b", note: null })).resolves.toEqual({ choice: "b" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/pages/some-slug/state?tz=Europe%2FLondon");
    expect(init.method).toBe("PATCH");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body as string)).toEqual({ fields: { choice: "b", note: null } });
  });

  it("recordOpen POSTs to its endpoint with keepalive", async () => {
    window.history.replaceState(null, "", "/some-slug");
    const fetchMock = vi.fn().mockResolvedValue(ok());
    vi.stubGlobal("fetch", fetchMock);

    vi.spyOn(performance, "getEntriesByType").mockReturnValue([]);
    setTimezone(undefined);

    await recordOpen();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/pages/some-slug/open");
    expect(init).toMatchObject({ method: "POST", keepalive: true });
  });

  it.each(["navigate", "reload", "back_forward"])("recordOpen sends kind=%s", async (type) => {
    window.history.replaceState(null, "", "/some-slug");
    const fetchMock = vi.fn().mockResolvedValue(ok());
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(performance, "getEntriesByType").mockReturnValue([
      { type } as PerformanceNavigationTiming,
    ]);
    setTimezone("Pacific/Auckland");

    await recordOpen();
    expect(fetchMock.mock.calls[0][0]).toBe(
      `/api/v1/pages/some-slug/open?kind=${type}&tz=Pacific%2FAuckland`,
    );
  });

  it("recordOpen omits kinds the server does not record", async () => {
    window.history.replaceState(null, "", "/some-slug");
    const fetchMock = vi.fn().mockResolvedValue(ok());
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(performance, "getEntriesByType").mockReturnValue([
      { type: "prerender" } as unknown as PerformanceNavigationTiming,
    ]);
    setTimezone(undefined);

    await recordOpen();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/pages/some-slug/open");
  });

  it.each([
    [422, "invalid"],
    [404, "unavailable"],
    [500, "failed"],
    [403, "failed"],
  ])("maps HTTP %i to %s", async (status, kind) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status }));
    expect(await failureKind(saveFields({ choice: "a" }))).toBe(kind);
  });

  it("reports a network failure as failed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    expect(await failureKind(recordOpen())).toBe("failed");
  });

  it("never reports success unless the server confirms the save", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok({ state: {}, saved: false })));
    expect(await failureKind(saveFields({ choice: "a" }))).toBe("failed");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.reject(new Error()) }),
    );
    expect(await failureKind(saveFields({ choice: "a" }))).toBe("failed");
  });
});
