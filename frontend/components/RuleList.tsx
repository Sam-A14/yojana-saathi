"use client";

import { useTranslations } from "next-intl";
import type { RuleResult } from "@/lib/types";

export type RuleMark = "met" | "notMet" | "notChecked";

const MARKS: Record<RuleMark, string> = { met: "✓", notMet: "✕", notChecked: "?" };

/** Rules as a list, each ticked, crossed or marked "not checked yet". The mark has a word for
 * screen readers, and the words themselves come from the rule text, not from colour. */
export function RuleList({
  rules,
  mark,
  describe,
}: {
  rules: RuleResult[];
  mark: RuleMark;
  describe: (rule: unknown) => string;
}) {
  const t = useTranslations("scheme");
  return (
    <ul className="flex flex-col gap-3">
      {rules.map((rule, index) => (
        <li key={index} className="flex gap-3">
          <span aria-hidden className="w-6 shrink-0 text-center text-xl font-bold">
            {MARKS[mark]}
          </span>
          <span className="sr-only">{t(`marks.${mark}`)}: </span>
          <span>
            {describe(rule.rule)}
            {mark === "notMet" && rule.fixable && (
              <span className="ml-2 inline-flex rounded-full border border-amber-600 px-2 text-sm font-semibold">
                {t("fixable")}
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
