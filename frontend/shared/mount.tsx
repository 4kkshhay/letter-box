import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import "./base.css";

/** Renders a page's root component into the `#root` element of its index.html. */
export function mountPage(page: ReactNode): void {
  const container = document.getElementById("root");
  if (!container) {
    throw new Error("Page index.html is missing its #root element");
  }
  createRoot(container).render(<StrictMode>{page}</StrictMode>);
}
