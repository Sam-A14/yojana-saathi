"use client";

import { ArrowLeft, ExternalLink } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useParams, useSearchParams } from "next/navigation";
import { benefitText, documentName, formatDate, notCheckedLines, schemeName } from "@/lib/format";
import { neededAnswers } from "@/lib/rules";
import type { DocumentInfo, Eligibility, ExcludedScheme, Family, MemberEligibility, SchemeResult } from "@/lib/types";
import { useFamilyResults } from "@/lib/use-family-results";
import { useFamily } from "@/lib/use-family";
import { useRuleText } from "@/lib/use-text";
import { Avatar } from "./Avatar";
import { DocumentIcon, SECTION_ICONS } from "./icons";
import { IconSection as Section } from "./IconSection";
import { NeededAnswers } from "./NeededAnswers";
import { RuleList } from "./RuleList";
import { StatusBadge, type ResultKind } from "./StatusBadge";
import { VerificationLabel } from "./VerificationLabel";
import { Button, ButtonLink, ErrorNote, Skeleton, buttonClass } from "./ui";

/** One scheme for one person: what it gives, why it may fit (each rule ticked or crossed), the
 * papers still missing, and where to check it officially. */
// Keyed by the family, like the dashboard (see there).
export function SchemeView() {
  const t = useTranslations("scheme");
  const td = useTranslations("dashboard");
  const { ready, family } = useFamily();

  if (!ready) return <Skeleton label={t("loading")} />;
  if (!family) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="page-title">{td("none")}</h1>
        <ButtonLink href="/signin">{td("toSignIn")}</ButtonLink>
      </div>
    );
  }
  return <SchemeScreen key={family.id} family={family} />;
}

function SchemeScreen({ family }: { family: Family }) {
  const t = useTranslations("scheme");
  const td = useTranslations("dashboard");
  const te = useTranslations("errors");
  const { slug } = useParams<{ slug: string }>();
  const memberId = useSearchParams().get("member");
  const { results, reload } = useFamilyResults(family);

  if (results.state === "loading") return <Skeleton label={t("loading")} />;
  if (results.state === "error") {
    return (
      <div className="flex flex-col gap-4">
        <ErrorNote>{te(results.kind)}</ErrorNote>
        {results.kind === "denied" || results.kind === "signedOut" ? <ButtonLink href="/signin">{td("toSignIn")}</ButtonLink> : <Button onClick={reload}>{td("retry")}</Button>}
      </div>
    );
  }
  return (
    <SchemeDetail
      eligibility={results.eligibility}
      documents={results.documents}
      slug={slug}
      memberId={memberId}
      backHref="/dashboard"
    />
  );
}

/** The scheme for one person, from results already in hand. Used for the real family and for the
 * example family (which needs no sign-in), so both look exactly the same. */
export function SchemeDetail({
  eligibility,
  documents,
  slug,
  memberId,
  backHref,
}: {
  eligibility: Eligibility;
  documents: DocumentInfo[];
  slug: string;
  memberId: string | null;
  backHref: string;
}) {
  const t = useTranslations("scheme");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const describe = useRuleText(documents);

  const back = (
    <ButtonLink href={backHref} variant="secondary">
      <ArrowLeft aria-hidden size={22} />
      {t("back")}
    </ButtonLink>
  );

  const member: MemberEligibility | undefined = eligibility.members.find((m) => m.member_id === memberId);
  const found: SchemeResult | undefined = member?.schemes.find((s) => s.scheme.slug === slug);
  const excluded: ExcludedScheme | undefined = member?.excluded.find((e) => e.scheme.slug === slug);
  if (!member || (!found && !excluded)) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="page-title">{memberId ? t("notFound") : t("chooseMember")}</h1>
        {back}
      </div>
    );
  }

  const scheme = (found ?? excluded)!.scheme;
  const kind: ResultKind = found ? found.status : "excluded";
  const summary = benefitText(scheme, locale);
  const notChecked = notCheckedLines(scheme, locale);
  const dates = [
    scheme.deadline_start && t("deadlineStarts", { date: formatDate(scheme.deadline_start, locale) }),
    scheme.deadline_end && t("deadlineEnds", { date: formatDate(scheme.deadline_end, locale) }),
  ].filter(Boolean);

  return (
    <article className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Avatar name={member.nickname} />
          <p className="text-lg font-bold text-muted">
            {scheme.for_whole_family ? t("forFamily") : t("forName", { name: member.nickname })}
          </p>
        </div>
        <h1 className="page-title">{schemeName(scheme, locale)}</h1>
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge kind={kind} />
          <VerificationLabel scheme={scheme} />
        </div>
        {!scheme.verified && <p>{t("unverifiedNote")}</p>}
      </div>

      <Section title={t("summaryTitle")} icon={SECTION_ICONS.summary}>
        <p>{summary ?? t("noSummary")}</p>
        {dates.map((line) => (
          <p key={String(line)} className="font-semibold">
            {line}
          </p>
        ))}
      </Section>

      {found && (
        <Section title={t("whyTitle")} icon={SECTION_ICONS.why}>
          {found.passed_rules.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-lg font-bold">{t("met")}</h3>
              <RuleList rules={found.passed_rules} mark="met" describe={describe} />
            </div>
          )}
          {found.failed_rules.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-lg font-bold">{t("notMet")}</h3>
              <RuleList rules={found.failed_rules} mark="notMet" describe={describe} />
            </div>
          )}
          {found.unknown_rules.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-lg font-bold">{t("notChecked")}</h3>
              <RuleList rules={found.unknown_rules} mark="notChecked" describe={describe} />
              <NeededAnswers needed={neededAnswers(found)} memberName={member.nickname} documents={documents} />
            </div>
          )}
        </Section>
      )}

      {excluded && (
        <Section title={t("excludedTitle")} icon={SECTION_ICONS.why}>
          <p className="font-semibold">{t("excludedBecause", { names: excluded.excluded_by.join(", ") })}</p>
          <RuleList rules={excluded.failed_rules} mark="notMet" describe={describe} />
        </Section>
      )}

      {/* Conditions this app cannot test. Shown for every result, "may qualify" included: that is
          where a family most needs to hear that the office will ask for more. */}
      {notChecked.length > 0 && (
        <Section title={t("notCheckedTitle")} icon={SECTION_ICONS.unchecked}>
          <p>{t("notCheckedIntro")}</p>
          <ul className="flex list-disc flex-col gap-2 pl-6">
            {notChecked.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Section>
      )}

      {found && (
        <Section title={t("docsTitle")} icon={SECTION_ICONS.docs}>
          {/* A whole-family scheme is opened for the first person: say whose papers these are. */}
          {scheme.for_whole_family && found.missing_documents.length > 0 && (
            <p className="font-semibold">{t("docsFor", { name: member.nickname })}</p>
          )}
          {found.missing_documents.length === 0 && <p>{t("docsNone")}</p>}
          <ul className="flex flex-col gap-4">
            {found.missing_documents.map((doc) => (
              <li key={doc.code} className="flex flex-col gap-1 rounded-2xl border border-line-soft bg-soft/60 p-4">
                <p className="flex items-center gap-3 text-lg font-bold">
                  <span aria-hidden className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                    <DocumentIcon code={doc.code} size={22} />
                  </span>
                  <span className="min-w-0 break-words">{documentName(documents, doc.code, locale)}</span>
                </p>
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

      <Section title={t("officialTitle")} icon={SECTION_ICONS.official}>
        <a href={scheme.official_url} target="_blank" rel="noopener noreferrer" className={buttonClass("primary")}>
          {t("openOfficial")}
          <ExternalLink aria-hidden size={20} />
        </a>
        {scheme.verified && scheme.verified_at && <p>{t("lastChecked", { date: formatDate(scheme.verified_at, locale) })}</p>}
      </Section>

      {back}
    </article>
  );
}
