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
      <span className="inline-flex rounded-full bg-close-bg px-4 py-1.5 text-base font-bold text-close-fg">
        {t("unverified")}
      </span>
    );
  }
  return (
    <span className="text-base text-muted">
      {t("verifiedOn", { date: formatDate(scheme.verified_at, locale) })}
    </span>
  );
}
