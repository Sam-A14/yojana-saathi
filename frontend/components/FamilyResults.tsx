"use client";

import { Users } from "lucide-react";
import { useTranslations } from "next-intl";
import type { FamilyResults as Family } from "@/lib/family-level";
import type { DocumentInfo } from "@/lib/types";
import { ResultGroups } from "./MemberResults";

/**
 * Schemes that depend on the whole family (the house, the village, "no one pays income tax"),
 * shown once above the people instead of on every card. The answer is the same for every member;
 * the scheme's own page is opened for the first member, whose papers it lists.
 */
export function FamilyResults({
  family,
  documents,
  schemeHref = (memberId, slug) => `/scheme/${slug}?member=${memberId}`,
}: {
  family: Family;
  documents: DocumentInfo[];
  schemeHref?: (memberId: string, slug: string) => string;
}) {
  const t = useTranslations("dashboard");
  if (!family.viaMemberId || !family.viaMemberName) return null;
  const via = family.viaMemberId;
  return (
    <section
      aria-labelledby="family-results"
      className="flex flex-col gap-5 rounded-3xl border border-line-soft bg-primary-soft/40 p-4 shadow-card"
    >
      <div className="flex items-center gap-4">
        <span aria-hidden className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
          <Users size={28} />
        </span>
        <div className="flex flex-col gap-1">
          <h2 id="family-results" className="text-2xl font-extrabold">
            {t("familyTitle")}
          </h2>
          <p className="text-base text-muted">{t("familyHint")}</p>
        </div>
      </div>
      <ResultGroups
        schemes={family.schemes}
        excluded={family.excluded}
        hrefFor={(slug) => schemeHref(via, slug)}
        askedName={family.viaMemberName}
        documents={documents}
      />
    </section>
  );
}
