import type { PageData } from "../../shared/api";
import styles from "./Page.module.css";

export function Page({ page }: { page: PageData }) {
  return (
    <main className={styles.page}>
      <h1>{page.title}</h1>
    </main>
  );
}
