import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const root = import.meta.dirname;
const pagesDir = resolve(root, "pages");

// Every directory under pages/ is a page, except underscore-prefixed ones
// (such as the scaffold template).
const pages = readdirSync(pagesDir, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && !entry.name.startsWith("_"))
  .map((entry) => entry.name);

// One build entry per page, plus the site root page.
const input: Record<string, string> = { index: resolve(root, "index.html") };
for (const name of pages) {
  const html = resolve(pagesDir, name, "index.html");
  if (!existsSync(html)) {
    throw new Error(`pages/${name} is missing index.html`);
  }
  input[name] = html;
}

/** Writes each page's page.json next to its built HTML, where the backend reads it. */
function pageConfigs(): Plugin {
  return {
    name: "letterbox-page-configs",
    apply: "build",
    generateBundle() {
      for (const name of pages) {
        this.emitFile({
          type: "asset",
          fileName: `pages/${name}/page.json`,
          source: readFileSync(resolve(pagesDir, name, "page.json")),
        });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), pageConfigs()],
  test: {
    environment: "jsdom",
  },
  build: {
    rolldownOptions: {
      input,
      output: {
        // Hash-only names: an asset URL says nothing about the page it belongs to.
        entryFileNames: "assets/[hash].js",
        chunkFileNames: "assets/[hash].js",
        assetFileNames: "assets/[hash][extname]",
      },
    },
  },
});
