import type { DocumentInfo, SchemeSummary } from "./types";

type Locale = "en" | "hi";

export const schemeName = (scheme: SchemeSummary, locale: Locale): string =>
  (locale === "hi" && scheme.name_hi) || scheme.name_en;

export const benefitText = (scheme: SchemeSummary, locale: Locale): string | null =>
  (locale === "hi" && scheme.benefit_text_hi) || scheme.benefit_text_en;

export const documentName = (documents: DocumentInfo[], code: string, locale: Locale): string => {
  const found = documents.find((d) => d.code === code);
  return found ? (locale === "hi" ? found.name_hi : found.name_en) : code;
};

/** "3 November 2026". The timezone is fixed to India so everyone sees the same day. */
export function formatDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale === "hi" ? "hi-IN" : "en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}
