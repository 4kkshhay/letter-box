import { useState, type CSSProperties } from "react";
import type { FieldDef, PageData } from "../../shared/api";
import { failureMessage, usePageState, type ActionStatus } from "../../shared/usePageState";
import styles from "./Page.module.css";

// Page-local only: not declared in page.json, so never sent or saved.
const ACCENTS = ["#b5523b", "#3f7d5c", "#3b5f9b"];

const optionsOf = (field: FieldDef | undefined) => (field && field.type !== "string" ? field.options : []);

/** Demo with auto-saved inputs and a local-only control. */
export function Page({ page }: { page: PageData }) {
  const { values, status, update, saveNow } = usePageState(page);
  const [accent, setAccent] = useState(0);

  const noteField = page.fields.note;
  const noteMax = noteField?.type === "string" ? noteField.max_length : 0;
  const note = typeof values.note === "string" ? values.note : "";
  const drinks = Array.isArray(values.drinks) ? values.drinks : [];

  const toggleDrink = (option: string) =>
    update(
      { drinks: drinks.includes(option) ? drinks.filter((d) => d !== option) : [...drinks, option] },
      { immediate: true },
    );

  return (
    <main className={styles.page} style={{ "--accent": ACCENTS[accent] } as CSSProperties}>
      <header className={styles.header}>
        <h1>{page.title}</h1>
        <p>Your answers save automatically and are shared with the page owner.</p>
      </header>

      <section className={styles.card}>
        <fieldset className={styles.group}>
          <legend>Favourite time of day</legend>
          <div className={styles.options}>
            {optionsOf(page.fields.time_of_day).map((option) => (
              <label key={option} className={styles.option}>
                <input
                  type="radio"
                  name="time_of_day"
                  value={option}
                  checked={values.time_of_day === option}
                  onChange={() => update({ time_of_day: option }, { immediate: true })}
                />
                <span>{option}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className={styles.group}>
          <legend>Drinks you enjoy</legend>
          <div className={styles.options}>
            {optionsOf(page.fields.drinks).map((option) => (
              <label key={option} className={styles.option}>
                <input
                  type="checkbox"
                  checked={drinks.includes(option)}
                  onChange={() => toggleDrink(option)}
                />
                <span>{option}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className={styles.group}>
          <span className={styles.legend}>A short note</span>
          <textarea
            className={styles.note}
            rows={3}
            maxLength={noteMax}
            value={note}
            onChange={(event) => update({ note: event.target.value })}
            onBlur={() => void saveNow()}
          />
          <span className={styles.hint}>
            {note.length}/{noteMax}
          </span>
        </label>

        <SaveStatus status={status} onRetry={() => void saveNow()} />
      </section>

      <section className={styles.card}>
        <h2>Local only</h2>
        <p>This changes the accent colour in this browser. It is never saved.</p>
        <button
          type="button"
          className={styles.secondary}
          onClick={() => setAccent((index) => (index + 1) % ACCENTS.length)}
        >
          Change colour
        </button>
      </section>
    </main>
  );
}

function SaveStatus({ status, onRetry }: { status: ActionStatus; onRetry: () => void }) {
  if (status.kind === "error") {
    return (
      <p className={styles.error} role="alert">
        {failureMessage(status.reason)}{" "}
        {status.reason === "failed" && (
          <button type="button" className={styles.link} onClick={onRetry}>
            Try again
          </button>
        )}
      </p>
    );
  }
  return (
    <p className={styles.status} role="status">
      {status.kind === "pending" ? "Saving…" : status.kind === "done" ? "Saved" : ""}
    </p>
  );
}
