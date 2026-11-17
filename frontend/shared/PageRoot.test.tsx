import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPage, PageUnavailableError, type PageData } from "./api";
import { goToRoot } from "./navigate";
import { PageRoot } from "./PageRoot";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  fetchPage: vi.fn(),
}));
vi.mock("./navigate", () => ({ goToRoot: vi.fn() }));

const fetchPageMock = vi.mocked(fetchPage);

const page: PageData = {
  title: "Loaded title",
  acknowledgement: false,
  fields: {},
  state: {},
  acknowledged: false,
};

const renderRoot = () => render(<PageRoot>{(data) => <h1>{data.title}</h1>}</PageRoot>);

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("PageRoot", () => {
  it("shows a loading view, then the page with its data", async () => {
    fetchPageMock.mockResolvedValue(page);
    renderRoot();

    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.queryByRole("heading")).toBeNull();

    expect(await screen.findByRole("heading", { name: "Loaded title" })).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows an error with a retry that loads the page", async () => {
    fetchPageMock.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(page);
    renderRoot();

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByRole("heading")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Loaded title" })).toBeTruthy();
    expect(fetchPageMock).toHaveBeenCalledTimes(2);
  });

  it("leaves for the site root when the page no longer exists", async () => {
    fetchPageMock.mockRejectedValue(new PageUnavailableError());
    renderRoot();

    await vi.waitFor(() => expect(goToRoot).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("uses a page's own loading and error views when given", async () => {
    fetchPageMock.mockRejectedValue(new Error("offline"));
    render(
      <PageRoot
        loading={<p>custom loading</p>}
        error={(retry) => <button onClick={retry}>custom retry</button>}
      >
        {(data) => <h1>{data.title}</h1>}
      </PageRoot>,
    );

    expect(screen.getByText("custom loading")).toBeTruthy();
    expect(await screen.findByRole("button", { name: "custom retry" })).toBeTruthy();
  });
});
