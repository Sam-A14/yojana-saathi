"use client";

import { ExternalLink } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { CategoryIcon, categoryKey } from "@/components/icons";
import { Card, buttonClass } from "@/components/ui";
import { VerificationLabel } from "@/components/VerificationLabel";
import { benefitText, formatDate, schemeName } from "@/lib/format";
import { STATES } from "@/lib/states";
import type { SchemeSummary } from "@/lib/types";

/**
 * One scheme from the catalogue (GET /schemes). It shows only what the API returned for it: the
 * name, category, who runs it (level and state), the benefit text and dates if there are any,
 * whether a person has checked it, and the official link. Nothing is filled in when a field is
 * missing, so an unchecked scheme can never look more certain than it is.
 * `showCategory` is switched off in a list already grouped by category, where it would repeat the heading.
 */
export function SchemeCard({ scheme, showCategory = true }: { scheme: SchemeSummary; showCategory?: boolean }) {
  const t = useTranslations("schemeCard");
  const ts = useTranslations("scheme");
  const tLanding = useTranslations("landing");
  const tCategory = useTranslations("categories");
  const locale = useLocale() === "hi" ? "hi" : "en";

  const benefit = benefitText(scheme, locale);
  const stateName = STATES.find((s) => s.code === scheme.state);
  const who =
    scheme.level === "central"
      ? t("central")
      : scheme.level === "state"
        ? stateName
          ? t("stateNamed", { state: locale === "hi" ? stateName.hi : stateName.en })
          : t("state")
        : null;
  const facts = [
    who,
    scheme.deadline_start && ts("deadlineStarts", { date: formatDate(scheme.deadline_start, locale) }),
    scheme.deadline_end && ts("deadlineEnds", { date: formatDate(scheme.deadline_end, locale) }),
  ].filter(Boolean);

  return (
    <Card className="flex h-full flex-col gap-4 transition duration-200 hover:-translate-y-1 hover:shadow-lift">
      {showCategory && (
        <div className="flex items-center gap-3">
          <span aria-hidden className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
            <CategoryIcon category={scheme.category} size={26} />
          </span>
          <span className="text-lg font-bold text-primary">{tCategory(categoryKey(scheme.category))}</span>
        </div>
      )}
      <h3 className="text-xl font-bold">{schemeName(scheme, locale)}</h3>
      {benefit && <p className="text-base text-muted">{benefit}</p>}
      {facts.length > 0 && (
        <ul className="flex flex-col gap-1 text-base font-semibold">
          {facts.map((fact) => (
            <li key={String(fact)}>{fact}</li>
          ))}
        </ul>
      )}
      <div className="mt-auto flex flex-col items-start gap-3">
        <VerificationLabel scheme={scheme} />
        <a
          href={scheme.official_url}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonClass("secondary", "w-full sm:w-auto")}
        >
          {tLanding("officialSite")}
          <ExternalLink aria-hidden size={20} />
        </a>
      </div>
    </Card>
  );
}
