import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { fetchPage, recordOpen } from "./api";
import { PageRoot } from "./PageRoot";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  fetchPage: vi.fn(),
  recordOpen: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("shows admin controls without reporting an open", async () => {
  window.history.replaceState({}, "", "/view/beta");
  vi.mocked(fetchPage).mockResolvedValue({
    title: "Beta",
    fields: {},
    state: {},
    admin: true,
  });

  render(<PageRoot>{(page) => <h1>{page.title}</h1>}</PageRoot>);

  await screen.findByRole("heading", { name: "Beta" });
  expect(screen.getByText("Read-only preview")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Reset page data" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "‹ Page stats" }).getAttribute("href")).toBe("/pages/beta");
  expect(document.querySelector("form")?.getAttribute("action")).toBe("/pages/beta/reset");
  expect(recordOpen).not.toHaveBeenCalled();
});
