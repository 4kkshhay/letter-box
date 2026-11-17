// Kept in its own file: the "already recorded" flag lives for the whole module,
// and each test file gets a fresh module. Tests here run in order.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPage, recordOpen, type PageData } from "./api";
import { PageRoot } from "./PageRoot";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  fetchPage: vi.fn(),
  recordOpen: vi.fn(),
}));

const page: PageData = {
  title: "Loaded title",
  fields: {},
  state: {},
};

const renderRoot = () => render(<PageRoot>{(data) => <h1>{data.title}</h1>}</PageRoot>);

afterEach(cleanup);

describe("PageRoot open recording", () => {
  it("records nothing while loading fails, then exactly one open once it loads", async () => {
    vi.mocked(recordOpen).mockRejectedValue(new Error("offline"));
    vi.mocked(fetchPage).mockRejectedValueOnce(new Error("offline")).mockResolvedValue(page);
    renderRoot();

    await screen.findByRole("alert");
    expect(recordOpen).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "Loaded title" });
    expect(recordOpen).toHaveBeenCalledTimes(1);
  });

  it("does not record again when the page mounts a second time", async () => {
    const callsBefore = vi.mocked(recordOpen).mock.calls.length;
    renderRoot();
    await screen.findByRole("heading", { name: "Loaded title" });
    expect(vi.mocked(recordOpen).mock.calls.length).toBe(callsBefore);
  });
});
