"use client";

import { SearchX } from "lucide-react";
import { useTranslations } from "next-intl";
import { MySchemeLink } from "./MySchemeLink";
import { ButtonLink } from "./ui";

/** Shown instead of the summary when we found nothing for anyone in the family (no scheme that may
 * fit, is close, needs an answer or is blocked). It says so plainly and offers the two useful next
 * steps: check the household details (they decide which schemes can match) or read the full list.
 * One main action (full width); the other is the quieter outline button. */
export function EmptyResults({
  checkedOn,
  quiet = false,
}: {
  checkedOn?: string;
  /** True when another button on the screen is the main action (the dashboard's "Add a family
   * member"): this one steps back to the outline look, so there is still only one. */
  quiet?: boolean;
}) {
  const t = useTranslations("dashboard");
  return (
    <section aria-labelledby="empty-results" className="flex flex-col gap-5 rounded-3xl border border-line-soft bg-soft p-5 shadow-card">
      <div className="flex items-start gap-4">
        <span aria-hidden className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
          <SearchX size={30} />
        </span>
        <div className="flex flex-col gap-2">
          <h2 id="empty-results" className="text-xl font-extrabold">
            {t("empty.title")}
          </h2>
          <p className="text-lg">{t("empty.body")}</p>
          {checkedOn && <p className="text-base text-muted">{t("checkedOn", { date: checkedOn })}</p>}
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <ButtonLink href="/household/edit" variant={quiet ? "secondary" : "primary"} className="w-full">
          {t("empty.review")}
        </ButtonLink>
        <ButtonLink href="/schemes" variant="secondary" className="w-full">
          {t("empty.allSchemes")}
        </ButtonLink>
        <MySchemeLink />
      </div>
    </section>
  );
}
