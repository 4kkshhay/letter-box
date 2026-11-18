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

/** The page directory whose page.json has this slug; read per request so new pages appear. */
function pageForSlug(slug: string): string | undefined {
  return readdirSync(pagesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith("_"))
    .map((entry) => entry.name)
    .find((name) => {
      try {
        const config = JSON.parse(readFileSync(resolve(pagesDir, name, "page.json"), "utf8"));
        return config.slug === slug;
      } catch {
        return false;
      }
    });
}

/** Dev server only: serve each page at its real link, /l/<slug>, as the site does. */
function pageLinks(): Plugin {
  return {
    name: "letterbox-page-links",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const match = /^\/l\/([a-z0-9-]+)\/?(\?.*)?$/.exec(req.url ?? "");
        const name = match ? pageForSlug(match[1]) : undefined;
        if (!name) {
          next();
          return;
        }
        try {
          // The URL stays /l/<slug> (the page reads it), so point relative
          // script and asset paths at the page directory.
          const source = readFileSync(resolve(pagesDir, name, "index.html"), "utf8");
          const html = await server.transformIndexHtml(
            req.url ?? "/",
            source.replace(/(src|href)="\.\//g, `$1="/pages/${name}/`),
          );
          res.setHeader("Content-Type", "text/html; charset=utf-8");
          res.setHeader("Cache-Control", "no-store");
          res.end(html);
        } catch (error) {
          next(error);
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), pageConfigs(), pageLinks()],
  server: {
    // Page API calls go to the running app, so pages load and save local data.
    // The Host header is kept, so the app's same-origin check still passes.
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://127.0.0.1:8610",
        changeOrigin: false,
        configure: (proxy) =>
          proxy.on("proxyReq", (proxyReq, req) => {
            if (req.headers.host) {
              proxyReq.setHeader("host", req.headers.host);
            }
          }),
      },
    },
    // Containers get no file-change events from a Windows-drive bind mount.
    watch: process.env.VITE_POLL ? { usePolling: true, interval: 300 } : undefined,
  },
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
