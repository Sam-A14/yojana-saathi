"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyResults } from "@/components/EmptyResults";
import { FamilyResults } from "@/components/FamilyResults";
import { FamilySummary } from "@/components/FamilySummary";
import { MemberActions } from "@/components/MemberActions";
import { MemberPanel } from "@/components/MemberPanel";
import { MemberResults } from "@/components/MemberResults";
import { MyData } from "@/components/MyData";
import { WhatsNew } from "@/components/WhatsNew";
import { Button, ButtonLink, Card, ErrorNote, Skeleton } from "@/components/ui";
import { api, errorKind, type ErrorKind } from "@/lib/api";
import { countResults, nothingFound, splitFamilyLevel } from "@/lib/family-level";
import { formatDate } from "@/lib/format";
import { MAX_MEMBERS } from "@/lib/options";
import { useFamilyResults } from "@/lib/use-family-results";
import { useFamily } from "@/lib/use-family";
import type { Session } from "@/lib/session";
import type { Family, Member } from "@/lib/types";

// Next.js can keep pages the person left (hidden, with their state) for Back/Forward. The screen is
// keyed by the family so that results loaded for one family can never be shown for another on a
// shared phone. (Precaution: I could not make a test fail without it; see tests/e2e/shared-phone.spec.ts.)
export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const { ready, family, session } = useFamily();
  const router = useRouter();

  // Signed in but no household yet: the first setup screen is the next step.
  useEffect(() => {
    if (ready && session && !family) router.replace("/setup/basics");
  }, [ready, session, family, router]);

  if (!ready || (session && !family)) return <Skeleton label={tc("loading")} />;
  if (!family || !session) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="page-title">{t("none")}</h1>
        <ButtonLink href="/signin">{t("toSignIn")}</ButtonLink>
        <ButtonLink href="/" variant="secondary">
          {t("toStart")}
        </ButtonLink>
      </div>
    );
  }
  return <DashboardScreen key={family.id} family={family} session={session} />;
}

// What the dashboard is showing instead of the results: nothing (the results), the form for a new
// person, a person being opened for editing, or that person's form. Only one thing at a time, so the
// screen has one main action.
type Panel = null | { kind: "add" } | { kind: "opening" } | { kind: "edit"; member: Member };

function DashboardScreen({ family, session }: { family: Family; session: Session }) {
  const t = useTranslations("dashboard");
  const te = useTranslations("errors");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const { results, reload } = useFamilyResults(family);
  // Schemes about the whole family are shown once, above the people (lib/family-level.ts).
  const split = results.state === "ready" ? splitFamilyLevel(results.eligibility) : null;
  const [panel, setPanel] = useState<Panel>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [problem, setProblem] = useState<ErrorKind | null>(null);
  const [removing, setRemoving] = useState(false);

  // The edit form needs the person's full details (birth year, work, ...); the results only carry
  // the name, so ask for the family's people when someone taps Edit.
  async function openEdit(memberId: string) {
    setNotice(null);
    setProblem(null);
    setPanel({ kind: "opening" });
    try {
      const found = (await api.listMembers(family)).find((m) => m.id === memberId);
      if (!found) throw new Error("gone");
      setPanel({ kind: "edit", member: found });
    } catch (error) {
      setProblem(errorKind(error));
      setPanel(null);
    }
  }

  async function remove(memberId: string, name: string) {
    setNotice(null);
    setProblem(null);
    setRemoving(true);
    try {
      await api.deleteMember(family, memberId);
      setNotice(t("memberRemoved", { name }));
      reload(); // the results are for the family as it was: ask again
    } catch (error) {
      setProblem(errorKind(error));
    }
    setRemoving(false);
  }

  function saved(person: Member, wasNew: boolean) {
    setPanel(null);
    setProblem(null);
    setNotice(t(wasNew ? "memberAdded" : "memberUpdated", { name: person.nickname }));
    reload();
  }

  if (panel?.kind === "opening") return <Skeleton label={t("openingMember")} />;
  if (panel) {
    return (
      <div className="flex flex-col gap-6">
        <Card>
          <MemberPanel
            family={family}
            member={panel.kind === "edit" ? panel.member : null}
            onDone={saved}
            onCancel={() => setPanel(null)}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="page-title">{t("title")}</h1>
      <div role="status" aria-live="polite">
        {notice && <p className="rounded-xl border-2 border-ok-fg bg-ok-bg px-4 py-3 text-lg font-semibold text-ok-fg">{notice}</p>}
      </div>
      {problem && <ErrorNote>{te(problem)}</ErrorNote>}

      <WhatsNew family={family} />

      {results.state === "loading" && <Skeleton label={t("loading")} />}

      {results.state === "error" && (
        <div className="flex flex-col gap-4">
          <ErrorNote>{te(results.kind)}</ErrorNote>
          {results.kind === "denied" || results.kind === "signedOut" ? (
            <ButtonLink href="/signin">{t("toSignIn")}</ButtonLink>
          ) : (
            <Button onClick={reload}>{t("retry")}</Button>
          )}
        </div>
      )}

      {results.state === "ready" && (
        <>
          {nothingFound(results.eligibility) ? (
            <EmptyResults checkedOn={formatDate(results.eligibility.computed_on, locale)} quiet />
          ) : (
            <>
              <FamilySummary
                counts={countResults(results.eligibility)}
                checkedOn={formatDate(results.eligibility.computed_on, locale)}
              />
              <ButtonLink href="/household/edit" variant="secondary">
                {t("editHousehold")}
              </ButtonLink>
            </>
          )}
          {results.eligibility.skipped_schemes.length > 0 && (
            <ErrorNote>{t("skipped", { count: results.eligibility.skipped_schemes.length })}</ErrorNote>
          )}
          {split && <FamilyResults family={split.family} documents={results.documents} />}
          <div className="grid items-start gap-6 md:grid-cols-2">
            {(split?.members ?? []).map((member) => (
              <MemberResults
                key={member.member_id}
                member={member}
                documents={results.documents}
                actions={
                  <MemberActions
                    name={member.nickname}
                    busy={removing}
                    onEdit={() => openEdit(member.member_id)}
                    onRemove={() => remove(member.member_id, member.nickname)}
                  />
                }
              />
            ))}
          </div>

          {/* The one main action of this screen: more people means more schemes found. */}
          <section aria-label={t("addMember")} className="flex flex-col gap-3">
            {results.eligibility.members.length >= MAX_MEMBERS ? (
              <p className="text-lg">{t("membersFull")}</p>
            ) : (
              <>
                <p className="text-lg">{t("addMemberHelp")}</p>
                <Button
                  onClick={() => {
                    setNotice(null);
                    setProblem(null);
                    setPanel({ kind: "add" });
                  }}
                >
                  <UserPlus aria-hidden size={22} />
                  {t("addMember")}
                </Button>
              </>
            )}
          </section>
        </>
      )}

      {/* Not while the results load: it sat under the grey placeholder and was pushed down when they
          arrived (a 0.247 layout shift). On an error it is shown, so a person can still sign out. */}
      {results.state !== "loading" && <MyData session={session} />}
    </div>
  );
}
