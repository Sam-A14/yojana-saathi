"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatDate } from "@/lib/format";
import type { SchemeSummary } from "@/lib/types";

/** "Not yet verified" until a person has checked the scheme's rules against the official source,
 * otherwise the date they last did. Never hidden: an unchecked scheme is still shown, honestly. */
export function VerificationLabel({ scheme }: { scheme: SchemeSummary }) {
  const t = useTranslations("status");
  const locale = useLocale() === "hi" ? "hi" : "en";
  if (!scheme.verified || !scheme.verified_at) {
    return (
      <span className="inline-flex rounded-full border border-amber-600 bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-950 dark:bg-amber-950 dark:text-amber-100">
        {t("unverified")}
      </span>
    );
  }
  return (
    <span className="text-sm text-zinc-600 dark:text-zinc-400">
      {t("verifiedOn", { date: formatDate(scheme.verified_at, locale) })}
    </span>
  );
}
