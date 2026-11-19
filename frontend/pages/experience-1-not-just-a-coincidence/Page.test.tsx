import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { NAME, SCENES } from "./content";
import { Page } from "./Page";

const page = { title: "", fields: {}, state: {} };

afterEach(cleanup);

const current = () => screen.getByRole("region");

describe("experience 1", () => {
  it("opens on the greeting", () => {
    render(<Page page={page} />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(NAME);
    expect(current().getAttribute("aria-label")).toBe(`1 of ${SCENES.length}`);
    expect(screen.getByRole("button", { name: "Previous" })).toHaveProperty("disabled", true);
  });

  it("moves with the keyboard and the story controls, within bounds", () => {
    render(<Page page={page} />);
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(current().getAttribute("aria-label")).toBe(`2 of ${SCENES.length}`);
    fireEvent.click(screen.getByRole("button", { name: "Previous" }));
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(current().getAttribute("aria-label")).toBe(`1 of ${SCENES.length}`);
    for (let n = 0; n < SCENES.length + 2; n++) {
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
    }
    expect(current().getAttribute("aria-label")).toBe(`${SCENES.length} of ${SCENES.length}`);
  });

  it("taps on the left third go back and elsewhere go forward; swipes follow the finger", () => {
    render(<Page page={page} />);
    const stage = screen.getByRole("main");
    const tap = (x: number) => {
      fireEvent.pointerDown(stage, { clientX: x, clientY: 300 });
      fireEvent.pointerUp(stage, { clientX: x, clientY: 300 });
    };
    tap(window.innerWidth - 10);
    expect(current().getAttribute("aria-label")).toBe(`2 of ${SCENES.length}`);
    tap(10);
    expect(current().getAttribute("aria-label")).toBe(`1 of ${SCENES.length}`);
    fireEvent.pointerDown(stage, { clientX: 300, clientY: 300 });
    fireEvent.pointerUp(stage, { clientX: 200, clientY: 310 });
    expect(current().getAttribute("aria-label")).toBe(`2 of ${SCENES.length}`);
  });
});
