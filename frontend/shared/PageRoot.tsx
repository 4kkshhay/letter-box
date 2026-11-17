import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { fetchPage, PageUnavailableError, recordOpen, type PageData } from "./api";
import { goToRoot } from "./navigate";
import styles from "./PageRoot.module.css";

type Status = { kind: "loading" } | { kind: "ready"; page: PageData } | { kind: "error" };

// One open per page load, even if the component mounts twice or a retry succeeds.
let openRecorded = false;

function recordOpenOnce(): void {
  if (openRecorded) {
    return;
  }
  openRecorded = true;
  // Losing an open is harmless; never disturb the page over it.
  recordOpen().catch(() => undefined);
}

interface PageRootProps {
  /** Renders the page once its data has loaded. */
  children: (page: PageData) => ReactNode;
  /** Replaces the default loading view. */
  loading?: ReactNode;
  /** Replaces the default error view. */
  error?: (retry: () => void) => ReactNode;
}

/**
 * Loads the page's data before rendering it, so saved values never flash in
 * after defaults. Shows a loading view meanwhile and a retry view on failure.
 */
export function PageRoot({ children, loading, error }: PageRootProps) {
  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchPage(controller.signal).then(
      (page) => {
        setStatus({ kind: "ready", page });
        if (!page.admin) {
          recordOpenOnce();
        }
      },
      (reason: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        if (reason instanceof PageUnavailableError) {
          // Same destination the server uses for unknown links.
          goToRoot();
          return;
        }
        setStatus({ kind: "error" });
      },
    );
    return () => controller.abort();
  }, [attempt]);

  const retry = () => {
    setStatus({ kind: "loading" });
    setAttempt((count) => count + 1);
  };

  if (status.kind === "ready") {
    const content = children(status.page);
    return status.page.admin ? <AdminPreview>{content}</AdminPreview> : content;
  }
  if (status.kind === "error") {
    return (
      error?.(retry) ?? (
        <div className={styles.center} role="alert">
          <p>This page could not be loaded. Check your connection and try again.</p>
          <button type="button" className={styles.retry} onClick={retry}>
            Try again
          </button>
        </div>
      )
    );
  }
  return (
    loading ?? (
      <div className={styles.center} role="status" aria-label="Loading">
        <span className={styles.dot} />
      </div>
    )
  );
}

function AdminPreview({ children }: { children: ReactNode }) {
  const page = window.location.pathname.split("/").filter(Boolean).at(-1) ?? "";
  const confirmReset = (event: FormEvent<HTMLFormElement>) => {
    if (!window.confirm("Reset all saved responses and opens for this page?")) {
      event.preventDefault();
    }
  };

  return (
    <>
      <nav className={styles.admin} aria-label="Admin preview controls">
        <a href="/">Dashboard</a>
        <span>Read-only preview</span>
        <form method="post" action={`/pages/${encodeURIComponent(page)}/reset`} onSubmit={confirmReset}>
          <button type="submit">Reset page data</button>
        </form>
      </nav>
      {children}
    </>
  );
}
