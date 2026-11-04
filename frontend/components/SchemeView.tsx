"use client";

import { useLocale, useTranslations } from "next-intl";
import { useParams, useSearchParams } from "next/navigation";
import { benefitText, documentName, formatDate, schemeName } from "@/lib/format";
import { neededAnswers } from "@/lib/rules";
import type { ExcludedScheme, Family, MemberEligibility, SchemeResult } from "@/lib/types";
import { useFamilyResults } from "@/lib/use-family-results";
import { useFamily } from "@/lib/use-family";
import { useRuleText } from "@/lib/use-text";
import { NeededAnswers } from "./NeededAnswers";
import { RuleList } from "./RuleList";
import { StatusBadge, type ResultKind } from "./StatusBadge";
import { VerificationLabel } from "./VerificationLabel";
import { Button, ButtonLink, ErrorNote, buttonClass } from "./ui";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xl font-bold">{title}</h2>
      {children}
    </section>
  );
}

/** One scheme for one person: what it gives, why it may fit (each rule ticked or crossed), the
 * papers still missing, and where to check it officially. */
// Keyed by the family, like the dashboard (see there).
export function SchemeView() {
  const t = useTranslations("scheme");
  const td = useTranslations("dashboard");
  const { ready, family } = useFamily();

  if (!ready) return <p role="status">{t("loading")}</p>;
  if (!family) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-2xl font-bold">{td("none")}</h1>
        <ButtonLink href="/resume">{td("toResume")}</ButtonLink>
      </div>
    );
  }
  return <SchemeScreen key={family.id} family={family} />;
}

function SchemeScreen({ family }: { family: Family }) {
  const t = useTranslations("scheme");
  const td = useTranslations("dashboard");
  const te = useTranslations("errors");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const { slug } = useParams<{ slug: string }>();
  const memberId = useSearchParams().get("member");
  const { results, reload } = useFamilyResults(family);
  const documents = results.state === "ready" ? results.documents : [];
  const describe = useRuleText(documents);

  const back = (
    <ButtonLink href="/dashboard" variant="secondary">
      {t("back")}
    </ButtonLink>
  );

  if (results.state === "loading") return <p role="status">{t("loading")}</p>;
  if (results.state === "error") {
    return (
      <div className="flex flex-col gap-4">
        <ErrorNote>{te(results.kind)}</ErrorNote>
        {results.kind === "denied" ? <ButtonLink href="/resume">{td("toResume")}</ButtonLink> : <Button onClick={reload}>{td("retry")}</Button>}
      </div>
    );
  }

  const member: MemberEligibility | undefined = results.eligibility.members.find((m) => m.member_id === memberId);
  const found: SchemeResult | undefined = member?.schemes.find((s) => s.scheme.slug === slug);
  const excluded: ExcludedScheme | undefined = member?.excluded.find((e) => e.scheme.slug === slug);
  if (!member || (!found && !excluded)) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-2xl font-bold">{memberId ? t("notFound") : t("chooseMember")}</h1>
        {back}
      </div>
    );
  }

  const scheme = (found ?? excluded)!.scheme;
  const kind: ResultKind = found ? found.status : "excluded";
  const summary = benefitText(scheme, locale);
  const dates = [
    scheme.deadline_start && t("deadlineStarts", { date: formatDate(scheme.deadline_start, locale) }),
    scheme.deadline_end && t("deadlineEnds", { date: formatDate(scheme.deadline_end, locale) }),
  ].filter(Boolean);

  return (
    <article className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <p className="text-base text-zinc-600 dark:text-zinc-400">{t("forName", { name: member.nickname })}</p>
        <h1 className="text-3xl font-bold">{schemeName(scheme, locale)}</h1>
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge kind={kind} />
          <VerificationLabel scheme={scheme} />
        </div>
        {!scheme.verified && <p>{t("unverifiedNote")}</p>}
      </div>

      <Section title={t("summaryTitle")}>
        <p>{summary ?? t("noSummary")}</p>
        {dates.map((line) => (
          <p key={String(line)} className="font-semibold">
            {line}
          </p>
        ))}
      </Section>

      {found && (
        <Section title={t("whyTitle")}>
          {found.passed_rules.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-bold">{t("met")}</h3>
              <RuleList rules={found.passed_rules} mark="met" describe={describe} />
            </div>
          )}
          {found.failed_rules.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-bold">{t("notMet")}</h3>
              <RuleList rules={found.failed_rules} mark="notMet" describe={describe} />
            </div>
          )}
          {found.unknown_rules.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="font-bold">{t("notChecked")}</h3>
              <RuleList rules={found.unknown_rules} mark="notChecked" describe={describe} />
              <NeededAnswers needed={neededAnswers(found)} memberName={member.nickname} documents={documents} />
            </div>
          )}
        </Section>
      )}

      {excluded && (
        <Section title={t("excludedTitle")}>
          <p className="font-semibold">{t("excludedBecause", { names: excluded.excluded_by.join(", ") })}</p>
          <RuleList rules={excluded.failed_rules} mark="notMet" describe={describe} />
        </Section>
      )}

      {found && (
        <Section title={t("docsTitle")}>
          {found.missing_documents.length === 0 && <p>{t("docsNone")}</p>}
          <ul className="flex flex-col gap-4">
            {found.missing_documents.map((doc) => (
              <li key={doc.code} className="flex flex-col gap-1 rounded-lg border border-zinc-300 p-4 dark:border-zinc-700">
                <p className="text-lg font-semibold">{documentName(documents, doc.code, locale)}</p>
                <p>{doc.state === "no" ? t("docNo") : t("docUnknown")}</p>
                {(locale === "hi" ? doc.how_to_get_hi : doc.how_to_get_en) && (
                  <p>
                    <span className="font-semibold">{t("howToGet")}: </span>
                    {locale === "hi" ? doc.how_to_get_hi : doc.how_to_get_en}
                  </p>
                )}
                {doc.official_link && (
                  <a href={doc.official_link} target="_blank" rel="noopener noreferrer" className="min-h-12 py-3 font-semibold underline">
                    {t("docLink")}
                  </a>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title={t("officialTitle")}>
        <a href={scheme.official_url} target="_blank" rel="noopener noreferrer" className={buttonClass("primary")}>
          {t("openOfficial")}
        </a>
        {scheme.verified && scheme.verified_at && <p>{t("lastChecked", { date: formatDate(scheme.verified_at, locale) })}</p>}
      </Section>

      {back}
    </article>
  );
}
