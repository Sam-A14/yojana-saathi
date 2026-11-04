"use client";

import { useTranslations } from "next-intl";

export type ResultKind = "eligible" | "near_miss" | "unknown" | "excluded";

// A mark and a word as well as a colour, so the meaning never depends on seeing colours.
const LOOK: Record<ResultKind, { mark: string; classes: string }> = {
  eligible: {
    mark: "✓",
    classes: "border-emerald-700 bg-emerald-50 text-emerald-950 dark:bg-emerald-950 dark:text-emerald-100",
  },
  near_miss: {
    mark: "≈",
    classes: "border-amber-600 bg-amber-50 text-amber-950 dark:bg-amber-950 dark:text-amber-100",
  },
  unknown: {
    mark: "?",
    classes: "border-sky-700 bg-sky-50 text-sky-950 dark:bg-sky-950 dark:text-sky-100",
  },
  excluded: {
    mark: "✕",
    classes: "border-red-700 bg-red-50 text-red-950 dark:bg-red-950 dark:text-red-100",
  },
};

export function StatusBadge({ kind }: { kind: ResultKind }) {
  const t = useTranslations("status");
  const { mark, classes } = LOOK[kind];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-sm font-semibold ${classes}`}>
      <span aria-hidden>{mark}</span>
      {t(kind)}
    </span>
  );
}
