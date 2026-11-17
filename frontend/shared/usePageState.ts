import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActionError,
  saveFields,
  type FailureKind,
  type FieldUpdate,
  type FieldValue,
  type PageData,
} from "./api";

export type ActionStatus =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "done" }
  | { kind: "error"; reason: FailureKind };

/** Default wording for a failed save; pages may use their own. */
export function failureMessage(reason: FailureKind): string {
  switch (reason) {
    case "invalid":
      return "Some answers could not be saved. Please check them and try again.";
    case "unavailable":
      return "This page is no longer available.";
    case "failed":
      return "That did not save. Check your connection and try again.";
  }
}

/** How long to wait after the last debounced change before saving. */
export const AUTOSAVE_DELAY_MS = 800;

const isEmpty = (fields: FieldUpdate) => Object.keys(fields).length === 0;

function applyUpdate(values: Record<string, FieldValue>, fields: FieldUpdate) {
  const next = { ...values };
  for (const [name, value] of Object.entries(fields)) {
    if (value === null) {
      delete next[name];
    } else {
      next[name] = value;
    }
  }
  return next;
}

/**
 * Page answers that save themselves.
 *
 * `update(fields)` shows the change at once and saves it in the background:
 * immediately with `{ immediate: true }` (choices), otherwise after a short
 * pause in changes (typing). Saves never overlap; changes made meanwhile are
 * sent next. Pending changes are also sent when the page is hidden or the
 * component unmounts. `status` reports saving, saved or why it failed; a
 * failed save is kept and sent again by `retry` or the next change, except
 * when the server rejected it as invalid.
 */
export function usePageState(page: PageData) {
  const readOnly = page.admin === true;
  const [values, setValues] = useState<Record<string, FieldValue>>(page.state);
  const [status, setStatus] = useState<ActionStatus>({ kind: "idle" });
  const unsaved = useRef<FieldUpdate>({});
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const saving = useRef(false);

  const flush = useCallback(async (): Promise<void> => {
    clearTimeout(timer.current);
    if (readOnly || saving.current || isEmpty(unsaved.current)) {
      return;
    }
    const fields = unsaved.current;
    unsaved.current = {};
    saving.current = true;
    setStatus({ kind: "pending" });
    let succeeded = false;
    try {
      await saveFields(fields);
      succeeded = true;
    } catch (error) {
      const reason = error instanceof ActionError ? error.kind : "failed";
      if (reason !== "invalid") {
        // Keep for a retry; newer changes to the same fields win.
        unsaved.current = { ...fields, ...unsaved.current };
      }
      setStatus({ kind: "error", reason });
    } finally {
      saving.current = false;
    }
    if (succeeded) {
      if (isEmpty(unsaved.current)) {
        setStatus({ kind: "done" });
      } else {
        await flush();
      }
    }
  }, [readOnly]);

  const update = useCallback(
    (fields: FieldUpdate, options: { immediate?: boolean } = {}) => {
      if (readOnly) {
        return;
      }
      setValues((current) => applyUpdate(current, fields));
      unsaved.current = { ...unsaved.current, ...fields };
      setStatus({ kind: "pending" });
      clearTimeout(timer.current);
      if (options.immediate) {
        void flush();
      } else {
        timer.current = setTimeout(() => void flush(), AUTOSAVE_DELAY_MS);
      }
    },
    [flush, readOnly],
  );

  useEffect(() => {
    const onHide = () => {
      if (document.visibilityState === "hidden") {
        void flush();
      }
    };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onHide);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onHide);
      void flush();
    };
  }, [flush]);

  /** Sends pending changes now, e.g. when a text field loses focus or after a failure. */
  const saveNow = flush;

  return { values, status, update, saveNow };
}
