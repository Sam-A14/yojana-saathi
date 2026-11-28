"use client";

import { useLocale, useTranslations } from "next-intl";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { schemeName } from "@/lib/format";
import { neededAnswers } from "@/lib/rules";
import { useRuleText } from "@/lib/use-text";
import type { DocumentInfo, ExcludedScheme, MemberEligibility, SchemeResult, SchemeSummary } from "@/lib/types";
import { Avatar } from "./Avatar";
import { CategoryIcon, StatusIcon, categoryKey } from "./icons";
import { NeededAnswers } from "./NeededAnswers";
import { RuleList } from "./RuleList";
import { StatusBadge, type ResultKind } from "./StatusBadge";
import { VerificationLabel } from "./VerificationLabel";

const GROUPS: SchemeResult["status"][] = ["eligible", "near_miss", "unknown"];

// A coloured edge on the left of each card, in the colour of its result. The chip says the same in
// an icon and a word, so the colour is never the only signal.
const EDGE: Record<ResultKind, string> = {
  eligible: "border-l-ok-fg",
  near_miss: "border-l-close-fg",
  unknown: "border-l-ask-fg",
  excluded: "border-l-block-fg",
};

export function SchemeRow({
  href,
  scheme,
  kind,
  children,
}: {
  href: string;
  scheme: SchemeSummary;
  kind: ResultKind;
  children?: React.ReactNode;
}) {
  const locale = useLocale() === "hi" ? "hi" : "en";
  const tCategory = useTranslations("categories");
  return (
    <li>
      <div
        className={`flex flex-col gap-3 rounded-2xl border border-l-8 border-line-soft bg-surface p-4 shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-lift ${EDGE[kind]}`}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-2 text-base font-bold text-primary">
            <span aria-hidden className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft">
              <CategoryIcon category={scheme.category} size={22} />
            </span>
            {tCategory(categoryKey(scheme.category))}
          </span>
          <StatusBadge kind={kind} />
        </div>
        <Link href={href} className="flex min-h-12 items-center justify-between gap-2 text-xl font-bold underline">
          {schemeName(scheme, locale)}
          <ChevronRight aria-hidden className="shrink-0" />
        </Link>
        <div>
          <VerificationLabel scheme={scheme} />
        </div>
        {children}
      </div>
    </li>
  );
}

/** The groups of results (may fit, close, needs an answer, blocked) as lists of schemes. Used for
 * one person's card and for the "whole family" section. */
export function ResultGroups({
  schemes,
  excluded,
  hrefFor,
  askedName,
  documents,
}: {
  schemes: SchemeResult[];
  excluded: ExcludedScheme[];
  hrefFor: (slug: string) => string;
  /** The name used in a question about one person (a family question does not use it). */
  askedName: string;
  documents: DocumentInfo[];
}) {
  const t = useTranslations("dashboard");
  const describe = useRuleText(documents);
  const byStatus = (kind: SchemeResult["status"]) => schemes.filter((s) => s.status === kind);

  return (
    <>
      {GROUPS.map((kind) => {
        const results = byStatus(kind);
        if (results.length === 0) return null;
        return (
          <div key={kind} className="flex flex-col gap-3">
            <h3 className="flex items-center gap-2 text-lg font-extrabold">
              <StatusIcon kind={kind} size={22} />
              {t(`sections.${kind}`)}
            </h3>
            <ul className="flex flex-col gap-3">
              {results.map((result) => (
                <SchemeRow key={result.scheme.slug} href={hrefFor(result.scheme.slug)} scheme={result.scheme} kind={kind}>
                  {kind === "near_miss" && (
                    <div>
                      <p className="font-semibold">{t("closeHint")}</p>
                      <RuleList
                        rules={result.failed_rules.filter((r) => r.fixable)}
                        mark="notMet"
                        describe={describe}
                      />
                    </div>
                  )}
                  {kind === "unknown" && (
                    <NeededAnswers needed={neededAnswers(result)} memberName={askedName} documents={documents} />
                  )}
                </SchemeRow>
              ))}
            </ul>
          </div>
        );
      })}

      {excluded.length > 0 && (
        <div className="flex flex-col gap-3">
          <h3 className="flex items-center gap-2 text-lg font-extrabold">
            <StatusIcon kind="excluded" size={22} />
            {t("sections.excluded")}
          </h3>
          <ul className="flex flex-col gap-3">
            {excluded.map((item) => (
              <SchemeRow key={item.scheme.slug} href={hrefFor(item.scheme.slug)} scheme={item.scheme} kind="excluded">
                <p>{t("excludedBecause", { names: item.excluded_by.join(", ") })}</p>
              </SchemeRow>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

/** One person's card: the schemes that may fit, are close, need an answer, or are blocked. */
export function MemberResults({
  member,
  documents,
  schemeHref = (memberId, slug) => `/scheme/${slug}?member=${memberId}`,
  actions,
}: {
  member: MemberEligibility;
  documents: DocumentInfo[];
  /** Where a scheme's own page is. The example family has its own pages (no sign-in needed). */
  schemeHref?: (memberId: string, slug: string) => string;
  /** Edit and Remove for this person (the example family has none: there is nobody to change). */
  actions?: React.ReactNode;
}) {
  const t = useTranslations("dashboard");
  const nothing = member.schemes.length === 0 && member.excluded.length === 0;

  return (
    <section
      aria-labelledby={`member-${member.member_id}`}
      className="flex flex-col gap-5 rounded-3xl border border-line-soft bg-soft/60 p-4 shadow-card"
    >
      <div className="flex items-center gap-4">
        <Avatar name={member.nickname} size="lg" />
        <h2 id={`member-${member.member_id}`} className="break-words text-2xl font-extrabold">
          {member.nickname}
        </h2>
      </div>
      {nothing && <p>{t("nothing", { name: member.nickname })}</p>}

      <ResultGroups
        schemes={member.schemes}
        excluded={member.excluded}
        hrefFor={(slug) => schemeHref(member.member_id, slug)}
        askedName={member.nickname}
        documents={documents}
      />

      {member.not_eligible_count > 0 && (
        <p className="text-base text-muted">
          {t("notFit", { count: member.not_eligible_count })}
        </p>
      )}
      {actions}
    </section>
  );
}
