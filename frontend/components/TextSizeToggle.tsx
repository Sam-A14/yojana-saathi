"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";
import { TEXT_SIZE_KEY } from "@/lib/text-size";

type Size = "normal" | "large";

// The size lives on <html> (data-text-size), because that is what the CSS reads. React watches it
// through useSyncExternalStore, so the buttons always match the page.
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => void listeners.delete(listener);
};
const currentSize = (): Size => (document.documentElement.dataset.textSize === "large" ? "large" : "normal");

function applySize(next: Size) {
  if (next === "large") document.documentElement.dataset.textSize = "large";
  else delete document.documentElement.dataset.textSize;
  try {
    localStorage.setItem(TEXT_SIZE_KEY, next);
  } catch {
    // Private mode or blocked storage: the size still changes now, it just is not remembered.
  }
  listeners.forEach((listener) => listener());
}

/** "A" / "A+": makes every word bigger. The choice is remembered on this phone only. */
export function TextSizeToggle({ onDark = false }: { onDark?: boolean }) {
  const t = useTranslations("textSize");
  // layout.tsx runs a tiny script before first paint that applies the saved size.
  const size = useSyncExternalStore(subscribe, currentSize, () => "normal" as Size);

  const border = onDark ? "border-on-hero/60" : "border-line";
  const pressed = onDark
    ? "aria-pressed:bg-on-hero aria-pressed:text-hero"
    : "aria-pressed:bg-primary aria-pressed:text-on-primary";
  return (
    <div role="group" aria-label={t("label")} className={`flex overflow-hidden rounded-xl border ${border}`}>
      {(["normal", "large"] as const).map((choice) => (
        <button
          key={choice}
          type="button"
          aria-pressed={size === choice}
          onClick={() => applySize(choice)}
          className={`min-h-12 min-w-12 px-3 text-base font-bold transition-colors ${pressed}`}
        >
          {choice === "normal" ? "A" : "A+"}
          <span className="sr-only"> {t(choice)}</span>
        </button>
      ))}
    </div>
  );
}
