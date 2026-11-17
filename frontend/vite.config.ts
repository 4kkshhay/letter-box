import { existsSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = import.meta.dirname;
const pagesDir = resolve(root, "pages");

// One build entry per page directory, plus the site root page.
const input: Record<string, string> = { index: resolve(root, "index.html") };
for (const entry of readdirSync(pagesDir, { withFileTypes: true })) {
  const html = resolve(pagesDir, entry.name, "index.html");
  if (entry.isDirectory() && existsSync(html)) {
    input[entry.name] = html;
  }
}

export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: { input },
  },
});
