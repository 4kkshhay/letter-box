/**
 * Everything this page says, in order. Bracketed text is a placeholder for
 * the real story; scenes can be added, removed or reordered freely.
 */
import recipient from "../../shared/recipient.json";

export const NAME = recipient.name || "you";

export interface Photo {
  /** An image imported from this directory; without one, a placeholder frame shows. */
  src?: string;
  alt: string;
  caption?: string;
}

export type Scene =
  | { kind: "greeting"; lines: string[] }
  | { kind: "chapter"; eyebrow: string; title: string; lines: string[]; photo?: Photo }
  | { kind: "closing"; lines: string[] };

export const SCENES: Scene[] = [
  { kind: "greeting", lines: ["[A line or two of welcome.]"] },
  {
    kind: "chapter",
    eyebrow: "Chapter one",
    title: "[Title]",
    lines: ["[How it began.]"],
  },
  {
    kind: "chapter",
    eyebrow: "Chapter two",
    title: "[Title]",
    lines: ["[The flowers.]"],
    photo: { alt: "[Photo of the flowers]", caption: "[Caption]" },
  },
  {
    kind: "chapter",
    eyebrow: "Chapter three",
    title: "[Title]",
    lines: ["[Why it could not be a coincidence.]"],
  },
  { kind: "closing", lines: ["[Closing — the shelf.]"] },
];
