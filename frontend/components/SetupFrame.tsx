"use client";

import { Check } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

const STEP_NAMES = ["basics", "members", "documents", "exclusions"] as const;

/** The progress shown above the four setup screens: four circles joined by a line (a tick for the
 * steps done, a filled circle for this one), and the same thing in words below, so progress never
 * depends on colour alone. */
export function SetupFrame({ step, children }: { step: 1 | 2 | 3 | 4; children: ReactNode }) {
  const t = useTranslations("steps");
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 print:hidden">
        <div
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={STEP_NAMES.length}
          aria-valuenow={step}
          aria-label={t(STEP_NAMES[step - 1])}
          className="flex items-center"
        >
          {STEP_NAMES.map((name, index) => {
            const number = index + 1;
            const done = number < step;
            const current = number === step;
            return (
              <div key={name} className={`flex items-center ${number < STEP_NAMES.length ? "flex-1" : ""}`}>
                <span
                  aria-hidden
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 text-lg font-extrabold transition ${
                    done
                      ? "border-primary bg-primary text-on-primary"
                      : current
                        ? "border-primary bg-primary-soft text-primary shadow-card ring-4 ring-primary/20"
                        : "border-line-soft bg-surface text-muted"
                  }`}
                >
                  {done ? <Check size={22} strokeWidth={3} /> : number}
                </span>
                {number < STEP_NAMES.length && (
                  <span aria-hidden className={`mx-1 h-1 flex-1 rounded-full ${done ? "bg-primary" : "bg-line-soft"}`} />
                )}
              </div>
            );
          })}
        </div>
        <p className="text-base font-semibold text-muted">
          {t("progress", { current: step, total: STEP_NAMES.length })}: {t(STEP_NAMES[step - 1])}
        </p>
      </div>
      {children}
    </section>
  );
}
