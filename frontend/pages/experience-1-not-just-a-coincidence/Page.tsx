import "@fontsource/cormorant-garamond/latin-400.css";
import "@fontsource/cormorant-garamond/latin-400-italic.css";
import "@fontsource/cormorant-garamond/latin-500.css";
import "@fontsource/pinyon-script/latin-400.css";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type PointerEvent } from "react";
import type { PageData } from "../../shared/api";
import { NAME, SCENES, type Photo, type Scene } from "./content";
import styles from "./Page.module.css";

const LEAVE_MS = 900;
const SWIPE_PX = 40;
const TAP_PX = 10;

type Direction = 1 | -1;

/** Stagger position of an animated element within its scene. */
const at = (step: number) => ({ "--i": step }) as CSSProperties;

/** A story told in full-screen scenes: tap right or swipe left for the next, tap left or swipe right to go back. */
export function Page(_props: { page: PageData }) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<Direction>(1);
  const [leaving, setLeaving] = useState<number | null>(null);
  const pointer = useRef<{ x: number; y: number } | null>(null);

  const go = useCallback(
    (step: Direction) => {
      const next = index + step;
      if (next < 0 || next >= SCENES.length) {
        return;
      }
      setLeaving(index);
      setDirection(step);
      setIndex(next);
    },
    [index],
  );

  useEffect(() => {
    if (leaving === null) {
      return;
    }
    const timer = window.setTimeout(() => setLeaving(null), LEAVE_MS);
    return () => window.clearTimeout(timer);
  }, [leaving]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") go(1);
      if (event.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  const onPointerDown = (event: PointerEvent) => {
    pointer.current = { x: event.clientX, y: event.clientY };
  };

  const onPointerUp = (event: PointerEvent) => {
    const start = pointer.current;
    pointer.current = null;
    if (!start || event.button > 0) {
      return;
    }
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.abs(dx) > SWIPE_PX && Math.abs(dx) > Math.abs(dy)) {
      go(dx < 0 ? 1 : -1);
    } else if (Math.abs(dx) < TAP_PX && Math.abs(dy) < TAP_PX) {
      go(event.clientX < window.innerWidth / 3 ? -1 : 1);
    }
  };

  return (
    <main
      className={styles.page}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerCancel={() => (pointer.current = null)}
    >
      <Petals />
      <ol className={styles.progress} aria-hidden="true">
        {SCENES.map((_, n) => (
          <li key={n} data-state={n < index ? "done" : n === index ? "now" : "next"} />
        ))}
      </ol>

      {leaving !== null && (
        <div key={`leaving-${leaving}`} className={`${styles.scene} ${styles.leaving}`} aria-hidden="true">
          <SceneView scene={SCENES[leaving]} />
        </div>
      )}
      <section
        key={index}
        className={`${styles.scene} ${styles.entering}`}
        data-direction={direction}
        aria-live="polite"
        aria-label={`${index + 1} of ${SCENES.length}`}
      >
        <SceneView scene={SCENES[index]} />
      </section>

      {index === 0 && (
        <p className={styles.hint} aria-hidden="true">
          tap to begin
        </p>
      )}
      <nav className={styles.controls} aria-label="Story">
        <button type="button" onClick={() => go(-1)} disabled={index === 0}>
          Previous
        </button>
        <button type="button" onClick={() => go(1)} disabled={index === SCENES.length - 1}>
          Next
        </button>
      </nav>
    </main>
  );
}

function SceneView({ scene }: { scene: Scene }) {
  if (scene.kind === "greeting") {
    return (
      <div className={styles.column}>
        <Sprig className={styles.sprig} />
        <p className={`${styles.hello} ${styles.reveal}`} style={at(1)}>
          Hello,
        </p>
        <h1 className={`${styles.name} ${styles.write}`} style={at(2)}>
          {NAME}
        </h1>
        <Lines lines={scene.lines} from={4} />
      </div>
    );
  }
  if (scene.kind === "chapter") {
    return (
      <article className={styles.column}>
        <p className={`${styles.eyebrow} ${styles.reveal}`} style={at(0)}>
          {scene.eyebrow}
        </p>
        <h2 className={`${styles.title} ${styles.write}`} style={at(1)}>
          {scene.title}
        </h2>
        <Divider step={2} />
        {scene.photo && <PhotoFrame photo={scene.photo} step={3} />}
        <Lines lines={scene.lines} from={scene.photo ? 4 : 3} />
      </article>
    );
  }
  return (
    <div className={styles.column}>
      <Lines lines={scene.lines} from={0} />
      <Divider step={scene.lines.length} />
    </div>
  );
}

function Lines({ lines, from }: { lines: string[]; from: number }) {
  return lines.map((line, n) => (
    <p key={n} className={`${styles.line} ${styles.reveal}`} style={at(from + n)}>
      {line}
    </p>
  ));
}

function Divider({ step }: { step: number }) {
  return (
    <svg className={`${styles.divider} ${styles.reveal}`} style={at(step)} viewBox="0 0 120 12" aria-hidden="true">
      <path d="M8 6h42M70 6h42" />
      <path d="M60 1.5l4.5 4.5-4.5 4.5-4.5-4.5z" />
    </svg>
  );
}

function PhotoFrame({ photo, step }: { photo: Photo; step: number }) {
  return (
    <figure className={`${styles.photo} ${styles.reveal}`} style={at(step)}>
      <div className={styles.frame}>
        {photo.src ? (
          <img src={photo.src} alt={photo.alt} />
        ) : (
          <span className={styles.placeholder}>{photo.alt}</span>
        )}
      </div>
      {photo.caption && <figcaption>{photo.caption}</figcaption>}
    </figure>
  );
}

/** A pressed-flower sprig whose stems draw themselves in. */
function Sprig({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 120 160" aria-hidden="true">
      <g className={styles.stems}>
        <path d="M60 156C58 122 66 94 60 60" />
        <path d="M61 106C72 94 84 88 95 80" />
        <path d="M59 124C48 114 38 110 27 106" />
      </g>
      <g className={styles.leaves}>
        <path d="M95 80c-11-1-19 5-21 13 10 1 18-4 21-13z" />
        <path d="M27 106c10-4 19 0 22 8-10 3-19 0-22-8z" />
        <path d="M61 140c10-7 21-5 25 1-9 7-20 6-25-1z" />
        <path d="M59 86c-9-7-20-6-24 0 8 7 19 7 24 0z" />
      </g>
      <g className={styles.bloom} transform="translate(60 44)">
        {[0, 72, 144, 216, 288].map((angle) => (
          <ellipse key={angle} rx="8.5" ry="14" cy="-12" transform={`rotate(${angle})`} />
        ))}
        <circle r="4.5" />
      </g>
    </svg>
  );
}

// Fixed positions and timings, so the drift looks the same on every visit.
const PETALS = [
  { left: 6, size: 13, fall: 21, delay: -4, sway: 18 },
  { left: 22, size: 9, fall: 26, delay: -15, sway: -14 },
  { left: 39, size: 15, fall: 23, delay: -9, sway: 22 },
  { left: 58, size: 10, fall: 28, delay: -20, sway: -18 },
  { left: 73, size: 14, fall: 20, delay: -1, sway: 16 },
  { left: 88, size: 11, fall: 25, delay: -12, sway: -20 },
];

function Petals() {
  return (
    <div className={styles.petals} aria-hidden="true">
      {PETALS.map((petal, n) => (
        <span
          key={n}
          style={
            {
              "--left": `${petal.left}%`,
              "--size": `${petal.size}px`,
              "--fall": `${petal.fall}s`,
              "--delay": `${petal.delay}s`,
              "--sway": `${petal.sway}px`,
            } as CSSProperties
          }
        >
          <svg viewBox="0 0 20 20">
            <path d="M10 1C16 5 17 13 10 19 3 13 4 5 10 1z" />
          </svg>
        </span>
      ))}
    </div>
  );
}
