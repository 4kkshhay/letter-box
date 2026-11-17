import { useEffect, useState, type ReactNode } from "react";
import { fetchPage, PageUnavailableError, type PageData } from "./api";
import { goToRoot } from "./navigate";
import styles from "./PageRoot.module.css";

type Status = { kind: "loading" } | { kind: "ready"; page: PageData } | { kind: "error" };

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
      (page) => setStatus({ kind: "ready", page }),
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
    return children(status.page);
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
