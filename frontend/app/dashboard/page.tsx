"use client";

import { useLocale, useTranslations } from "next-intl";
import { MemberResults } from "@/components/MemberResults";
import { MyData } from "@/components/MyData";
import { Button, ButtonLink, ErrorNote } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useFamilyResults } from "@/lib/use-family-results";
import { useFamily } from "@/lib/use-family";
import type { Eligibility, Family } from "@/lib/types";

// How many (person, scheme) results fall in each group, across the whole family.
function count(eligibility: Eligibility) {
  const all = eligibility.members.flatMap((m) => m.schemes);
  const of = (status: string) => all.filter((s) => s.status === status).length;
  return { fit: of("eligible"), close: of("near_miss"), unsure: of("unknown") };
}

// Next.js can keep pages the person left (hidden, with their state) for Back/Forward. The screen is
// keyed by the family so that results loaded for one family can never be shown for another on a
// shared phone. (Precaution: I could not make a test fail without it; see tests/e2e/shared-phone.spec.ts.)
export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const { ready, family } = useFamily();

  if (!ready) return <p role="status">{tc("loading")}</p>;
  if (!family) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-2xl font-bold">{t("none")}</h1>
        <ButtonLink href="/resume">{t("toResume")}</ButtonLink>
        <ButtonLink href="/" variant="secondary">
          {t("toStart")}
        </ButtonLink>
      </div>
    );
  }
  return <DashboardScreen key={family.id} family={family} />;
}

function DashboardScreen({ family }: { family: Family }) {
  const t = useTranslations("dashboard");
  const te = useTranslations("errors");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const { results, reload } = useFamilyResults(family);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-bold">{t("title")}</h1>

      {results.state === "loading" && <p role="status">{t("loading")}</p>}

      {results.state === "error" && (
        <div className="flex flex-col gap-4">
          <ErrorNote>{te(results.kind)}</ErrorNote>
          {results.kind === "denied" ? (
            <ButtonLink href="/resume">{t("toResume")}</ButtonLink>
          ) : (
            <Button onClick={reload}>{t("retry")}</Button>
          )}
        </div>
      )}

      {results.state === "ready" && (
        <>
          <div className="flex flex-col gap-1">
            <p className="text-lg">{t("summary", count(results.eligibility))}</p>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {t("checkedOn", { date: formatDate(results.eligibility.computed_on, locale) })}
            </p>
          </div>
          <ButtonLink href="/household/edit" variant="secondary">
            {t("editHousehold")}
          </ButtonLink>
          {results.eligibility.skipped_schemes.length > 0 && (
            <ErrorNote>{t("skipped", { count: results.eligibility.skipped_schemes.length })}</ErrorNote>
          )}
          {results.eligibility.members.map((member) => (
            <MemberResults key={member.member_id} member={member} documents={results.documents} />
          ))}
        </>
      )}

      <MyData family={family} />
    </div>
  );
}
