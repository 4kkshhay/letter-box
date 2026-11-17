import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ActionError, saveFields, type PageData } from "./api";
import { AUTOSAVE_DELAY_MS, failureMessage, usePageState } from "./usePageState";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  saveFields: vi.fn(),
}));

const saveMock = vi.mocked(saveFields);

const page: PageData = {
  title: "T",
  fields: {
    choice: { type: "enum", options: ["a", "b"] },
    note: { type: "string", max_length: 100 },
  },
  state: { choice: "a" },
};

/** Lets pending promise callbacks run. */
const settle = () => act(async () => {});

beforeEach(() => {
  vi.useFakeTimers();
  saveMock.mockResolvedValue({});
});

afterEach(() => {
  vi.useRealTimers();
  vi.resetAllMocks();
});

describe("usePageState", () => {
  it("starts from the saved values without saving anything", () => {
    const { result } = renderHook(() => usePageState(page));
    expect(result.current.values).toEqual({ choice: "a" });
    expect(result.current.status).toEqual({ kind: "idle" });
    expect(saveMock).not.toHaveBeenCalled();
  });

  it("saves an immediate change at once and shows it before the server answers", async () => {
    const { result } = renderHook(() => usePageState(page));
    act(() => result.current.update({ choice: "b" }, { immediate: true }));

    expect(result.current.values).toEqual({ choice: "b" });
    expect(result.current.status).toEqual({ kind: "pending" });
    expect(saveMock).toHaveBeenCalledWith({ choice: "b" });

    await settle();
    expect(result.current.status).toEqual({ kind: "done" });
  });

  it("waits for a pause in typing and sends only the latest text", async () => {
    const { result } = renderHook(() => usePageState(page));
    act(() => result.current.update({ note: "h" }));
    act(() => result.current.update({ note: "hi" }));
    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS - 1));
    expect(saveMock).not.toHaveBeenCalled();

    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(saveMock).toHaveBeenCalledTimes(1);
    expect(saveMock).toHaveBeenCalledWith({ note: "hi" });
  });

  it("saveNow sends pending text without waiting", async () => {
    const { result } = renderHook(() => usePageState(page));
    act(() => result.current.update({ note: "hi" }));
    await act(() => result.current.saveNow());
    expect(saveMock).toHaveBeenCalledWith({ note: "hi" });
  });

  it("never overlaps saves and sends changes made meanwhile afterwards", async () => {
    let finishFirst: (value: Record<string, never>) => void = () => undefined;
    saveMock.mockImplementationOnce(() => new Promise((resolve) => (finishFirst = resolve)));
    const { result } = renderHook(() => usePageState(page));

    act(() => result.current.update({ choice: "b" }, { immediate: true }));
    act(() => result.current.update({ note: "x" }, { immediate: true }));
    expect(saveMock).toHaveBeenCalledTimes(1);

    await act(async () => finishFirst({}));
    expect(saveMock).toHaveBeenCalledTimes(2);
    expect(saveMock).toHaveBeenLastCalledWith({ note: "x" });
    await settle();
    expect(result.current.status).toEqual({ kind: "done" });
  });

  it("removes a value locally when cleared with null", () => {
    const { result } = renderHook(() => usePageState(page));
    act(() => result.current.update({ choice: null }, { immediate: true }));
    expect(result.current.values).toEqual({});
    expect(saveMock).toHaveBeenCalledWith({ choice: null });
  });

  it("reports a failed save, keeps the change and resends it on retry", async () => {
    saveMock.mockRejectedValueOnce(new ActionError("failed"));
    const { result } = renderHook(() => usePageState(page));

    act(() => result.current.update({ choice: "b" }, { immediate: true }));
    await settle();
    expect(result.current.status).toEqual({ kind: "error", reason: "failed" });
    expect(result.current.values).toEqual({ choice: "b" });

    await act(() => result.current.saveNow());
    expect(saveMock).toHaveBeenCalledTimes(2);
    expect(saveMock).toHaveBeenLastCalledWith({ choice: "b" });
    expect(result.current.status).toEqual({ kind: "done" });
  });

  it("merges a failed change with newer ones, newest winning", async () => {
    saveMock.mockRejectedValueOnce(new Error("offline"));
    const { result } = renderHook(() => usePageState(page));

    act(() => result.current.update({ choice: "b", note: "old" }, { immediate: true }));
    await settle();
    act(() => result.current.update({ note: "new" }, { immediate: true }));
    await settle();
    expect(saveMock).toHaveBeenLastCalledWith({ choice: "b", note: "new" });
  });

  it("does not resend a change the server rejected as invalid", async () => {
    saveMock.mockRejectedValueOnce(new ActionError("invalid"));
    const { result } = renderHook(() => usePageState(page));

    act(() => result.current.update({ choice: "b" }, { immediate: true }));
    await settle();
    expect(result.current.status).toEqual({ kind: "error", reason: "invalid" });

    await act(() => result.current.saveNow());
    expect(saveMock).toHaveBeenCalledTimes(1);
  });

  it("sends pending changes when the page is hidden", async () => {
    const { result } = renderHook(() => usePageState(page));
    act(() => result.current.update({ note: "hi" }));

    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(saveMock).toHaveBeenCalledWith({ note: "hi" });
  });

  it("sends pending changes on unmount", () => {
    const { result, unmount } = renderHook(() => usePageState(page));
    act(() => result.current.update({ note: "hi" }));
    unmount();
    expect(saveMock).toHaveBeenCalledWith({ note: "hi" });
  });
});

describe("failureMessage", () => {
  it("has wording for every failure kind", () => {
    for (const kind of ["invalid", "unavailable", "failed"] as const) {
      expect(failureMessage(kind).length).toBeGreaterThan(0);
    }
  });
});
