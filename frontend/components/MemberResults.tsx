"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { schemeName } from "@/lib/format";
import { neededAnswers } from "@/lib/rules";
import { useRuleText } from "@/lib/use-text";
import type { DocumentInfo, MemberEligibility, SchemeResult, SchemeSummary } from "@/lib/types";
import { NeededAnswers } from "./NeededAnswers";
import { RuleList } from "./RuleList";
import { VerificationLabel } from "./VerificationLabel";

const GROUPS: SchemeResult["status"][] = ["eligible", "near_miss", "unknown"];

function SchemeRow({
  href,
  scheme,
  children,
}: {
  href: string;
  scheme: SchemeSummary;
  children?: React.ReactNode;
}) {
  const locale = useLocale() === "hi" ? "hi" : "en";
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-zinc-300 p-4 dark:border-zinc-700">
      <Link
        href={href}
        className="min-h-12 text-lg font-semibold underline"
      >
        {schemeName(scheme, locale)}
      </Link>
      <div>
        <VerificationLabel scheme={scheme} />
      </div>
      {children}
    </li>
  );
}

/** One person's card: the schemes that may fit, are close, need an answer, or are blocked. */
export function MemberResults({
  member,
  documents,
  schemeHref = (memberId, slug) => `/scheme/${slug}?member=${memberId}`,
}: {
  member: MemberEligibility;
  documents: DocumentInfo[];
  /** Where a scheme's own page is. The example family has its own pages (no sign-in needed). */
  schemeHref?: (memberId: string, slug: string) => string;
}) {
  const t = useTranslations("dashboard");
  const describe = useRuleText(documents);
  const byStatus = (kind: SchemeResult["status"]) => member.schemes.filter((s) => s.status === kind);
  const nothing = member.schemes.length === 0 && member.excluded.length === 0;

  return (
    <section
      aria-labelledby={`member-${member.member_id}`}
      className="flex flex-col gap-5 rounded-lg border-2 border-zinc-300 p-4 dark:border-zinc-700"
    >
      <h2 id={`member-${member.member_id}`} className="text-2xl font-bold">
        {member.nickname}
      </h2>
      {nothing && <p>{t("nothing", { name: member.nickname })}</p>}

      {GROUPS.map((kind) => {
        const results = byStatus(kind);
        if (results.length === 0) return null;
        return (
          <div key={kind} className="flex flex-col gap-3">
            <h3 className="text-lg font-bold">{t(`sections.${kind}`)}</h3>
            <ul className="flex flex-col gap-3">
              {results.map((result) => (
                <SchemeRow
                  key={result.scheme.slug}
                  href={schemeHref(member.member_id, result.scheme.slug)}
                  scheme={result.scheme}
                >
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
                    <NeededAnswers
                      needed={neededAnswers(result)}
                      memberName={member.nickname}
                      documents={documents}
                    />
                  )}
                </SchemeRow>
              ))}
            </ul>
          </div>
        );
      })}

      {member.excluded.length > 0 && (
        <div className="flex flex-col gap-3">
          <h3 className="text-lg font-bold">{t("sections.excluded")}</h3>
          <ul className="flex flex-col gap-3">
            {member.excluded.map((item) => (
              <SchemeRow key={item.scheme.slug} href={schemeHref(member.member_id, item.scheme.slug)} scheme={item.scheme}>
                <p>{t("excludedBecause", { names: item.excluded_by.join(", ") })}</p>
              </SchemeRow>
            ))}
          </ul>
        </div>
      )}

      {member.not_eligible_count > 0 && (
        <p className="text-zinc-600 dark:text-zinc-400">
          {t("notFit", { count: member.not_eligible_count })}
        </p>
      )}
    </section>
  );
}
