import { useState } from "react";
import type { PageData } from "../../shared/api";
import styles from "./Page.module.css";

/** Synthetic page added to verify new deploys leave existing pages untouched. */
export function Page({ page }: { page: PageData }) {
  const [count, setCount] = useState(0);

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <p className={styles.eyebrow}>Deployment check</p>
        <h1>{page.title}</h1>
        <p>This page was added after the original demos to check that old links remain intact.</p>
        <button type="button" onClick={() => setCount((value) => value + 1)}>
          Local count: {count}
        </button>
        <p className={styles.note}>The count stays in this browser and is never saved.</p>
      </section>
    </main>
  );
}
