import { useState } from "react";
import type { PageData } from "../../shared/api";
import styles from "./Page.module.css";

/** Demo without inputs: everything here is local to the browser and nothing is saved. */
export function Page({ page }: { page: PageData }) {
  const [open, setOpen] = useState(false);

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <h1 className={styles.title}>{page.title}</h1>
        <p className={styles.lead}>A page with no saved inputs.</p>

        <div className={styles.reveal} data-open={open} id="demo-details">
          <div className={styles.revealInner}>
            <p>
              This content is revealed in the browser only. Reloading the page starts over, and
              nothing is sent to the server.
            </p>
          </div>
        </div>

        <button
          type="button"
          className={styles.button}
          aria-expanded={open}
          aria-controls="demo-details"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Close" : "Open"}
        </button>
      </section>
    </main>
  );
}
