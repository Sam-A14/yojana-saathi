"use client";

import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";
import { describeRule, toTranslate, type Translate } from "./rule-text";
import type { DocumentInfo } from "./types";

/** A translator that takes any message key as text (for keys built at run time, such as
 * `questions.${field}`). A key we do not have comes back as the key itself, never as an error. */
export function useText(): Translate {
  const t = useTranslations();
  return useMemo(() => toTranslate(t), [t]);
}

/** Rule JSON in words, in the current language. `documents` supplies the paper names. */
export function useRuleText(documents: DocumentInfo[]): (rule: unknown) => string {
  const translate = useText();
  const locale = useLocale() === "hi" ? "hi" : "en";
  return useMemo(() => {
    const names = new Map(documents.map((d) => [d.code, locale === "hi" ? d.name_hi : d.name_en]));
    const documentName = (code: string) => names.get(code) ?? code;
    return (rule) => describeRule(rule, { translate, locale, documentName });
  }, [translate, locale, documents]);
}
