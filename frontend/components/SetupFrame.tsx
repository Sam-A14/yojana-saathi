"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

const STEP_NAMES = ["basics", "members", "documents", "exclusions"] as const;

/** The progress line and bar shared by the four setup screens. */
export function SetupFrame({ step, children }: { step: 1 | 2 | 3 | 4; children: ReactNode }) {
  const t = useTranslations("steps");
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 print:hidden">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {t("progress", { current: step, total: STEP_NAMES.length })}: {t(STEP_NAMES[step - 1])}
        </p>
        <div
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={STEP_NAMES.length}
          aria-valuenow={step}
          aria-label={t(STEP_NAMES[step - 1])}
          className="h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
        >
          <div className="h-full bg-emerald-700" style={{ width: `${(step / STEP_NAMES.length) * 100}%` }} />
        </div>
      </div>
      {children}
    </section>
  );
}
