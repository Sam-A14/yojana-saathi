"use client";

import { Check, CircleHelp, X, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { RuleResult } from "@/lib/types";

export type RuleMark = "met" | "notMet" | "notChecked";

// A tick, a cross or a question mark, each in a round badge of its own colour. The badge is
// decoration: the rule is written in words, and a screen reader also hears "Met:", "Not met:" or
// "Not checked yet:" before it.
const MARKS: Record<RuleMark, { Icon: LucideIcon; badge: string }> = {
  met: { Icon: Check, badge: "bg-ok-bg text-ok-fg" },
  notMet: { Icon: X, badge: "bg-block-bg text-block-fg" },
  notChecked: { Icon: CircleHelp, badge: "bg-ask-bg text-ask-fg" },
};

/** Rules as a checklist, each ticked, crossed or marked "not checked yet". */
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
  const { Icon, badge } = MARKS[mark];
  return (
    <ul className="flex flex-col gap-3">
      {rules.map((rule, index) => (
        <li key={index} className="flex items-start gap-3">
          <span aria-hidden className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${badge}`}>
            <Icon size={20} strokeWidth={3} />
          </span>
          <span className="sr-only">{t(`marks.${mark}`)}: </span>
          <span>
            {describe(rule.rule)}
            {mark === "notMet" && rule.fixable && (
              <span className="ml-2 inline-flex rounded-full border border-close-fg bg-close-bg px-3 text-base font-semibold text-close-fg">
                {t("fixable")}
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
