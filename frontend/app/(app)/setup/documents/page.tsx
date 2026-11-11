"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { SetupFrame } from "@/components/SetupFrame";
import { Button, ButtonLink, ErrorNote, YesNoGroup } from "@/components/ui";
import { api, errorKind, type ErrorKind } from "@/lib/api";
import type { DocumentInfo, Member } from "@/lib/types";
import { useSetupFamily } from "@/lib/use-setup-family";

// true = has it, false = does not, null = not sure (the API stores nothing for it).
type Answers = Record<string, boolean | null>;

type Loaded = {
  members: Member[];
  documents: DocumentInfo[];
  household: Answers; // asked once, for the whole family
  byMember: Record<string, Answers>;
};

// One family paper (ration card...) is shared by the whole home. If any member is already marked
// as having it, the family has it. Otherwise "no" if anyone said no, else not answered.
function householdAnswer(members: Member[], code: string): boolean | null {
  const answers = members.map((m) => m.documents[code]);
  if (answers.includes(true)) return true;
  if (answers.includes(false)) return false;
  return null;
}

function startingAnswers(members: Member[], documents: DocumentInfo[]): Loaded {
  const household: Answers = {};
  const byMember: Record<string, Answers> = {};
  for (const doc of documents.filter((d) => d.household_level)) {
    household[doc.code] = householdAnswer(members, doc.code);
  }
  for (const member of members) {
    byMember[member.id] = {};
    for (const doc of documents.filter((d) => !d.household_level)) {
      byMember[member.id][doc.code] = member.documents[doc.code] ?? null;
    }
  }
  return { members, documents, household, byMember };
}

// Leave out "not sure": PUT replaces everything, and a missing code means "not answered".
function onlyAnswered(answers: Answers): Record<string, boolean> {
  const answered: Record<string, boolean> = {};
  for (const [code, has] of Object.entries(answers)) {
    if (has !== null) answered[code] = has;
  }
  return answered;
}

export default function DocumentsPage() {
  const t = useTranslations("documents");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const family = useSetupFamily();

  const [data, setData] = useState<Loaded | null>(null);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<ErrorKind | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    Promise.all([api.listMembers(family), api.listDocuments()])
      .then(([members, documents]) => {
        if (!cancelled) setData(startingAnswers(members, documents));
      })
      .catch((error) => {
        if (!cancelled) setProblem(errorKind(error));
      });
    return () => {
      cancelled = true;
    };
  }, [family]);

  async function save() {
    if (!family || !data) return;
    setSaving(true);
    setProblem(null);
    try {
      // The family-level answers are written for every member, so each person's record agrees
      // (a "no" is then a real "no" for everyone, not "never asked").
      await Promise.all(
        data.members.map((member) =>
          api.setDocuments(
            family,
            member.id,
            onlyAnswered({ ...data.household, ...data.byMember[member.id] }),
          ),
        ),
      );
    } catch (error) {
      setProblem(errorKind(error));
      setSaving(false);
      return;
    }
    router.push("/setup/exclusions");
  }

  if (!data) return problem ? <ErrorNote>{te(problem)}</ErrorNote> : <p>{tc("loading")}</p>;

  const name = (doc: DocumentInfo) => (locale === "hi" ? doc.name_hi : doc.name_en);
  const labels = { yes: tc("yes"), no: tc("no"), notSure: tc("notSure") };
  const familyDocs = data.documents.filter((d) => d.household_level);
  const personalDocs = data.documents.filter((d) => !d.household_level);

  return (
    <SetupFrame step={3}>
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p>{t("intro")}</p>

      {familyDocs.length > 0 && (
        <section className="flex flex-col gap-5 rounded-lg border border-zinc-300 p-4 dark:border-zinc-700">
          <h2 className="text-xl font-bold">{t("householdTitle")}</h2>
          <p>{t("householdIntro")}</p>
          {familyDocs.map((doc) => (
            <YesNoGroup
              key={doc.code}
              legend={name(doc)}
              value={data.household[doc.code]}
              labels={labels}
              onChange={(has) => setData({ ...data, household: { ...data.household, [doc.code]: has } })}
            />
          ))}
        </section>
      )}

      {data.members.map((member, index) => (
        <details
          key={member.id}
          open={index === 0}
          className="rounded-lg border border-zinc-300 p-4 dark:border-zinc-700"
        >
          <summary className="min-h-12 cursor-pointer text-xl font-bold">
            {t("memberTitle", { name: member.nickname })}
          </summary>
          <div className="mt-4 flex flex-col gap-5">
            {personalDocs.map((doc) => (
              <YesNoGroup
                key={doc.code}
                legend={name(doc)}
                value={data.byMember[member.id][doc.code]}
                labels={labels}
                onChange={(has) =>
                  setData({
                    ...data,
                    byMember: {
                      ...data.byMember,
                      [member.id]: { ...data.byMember[member.id], [doc.code]: has },
                    },
                  })
                }
              />
            ))}
          </div>
        </details>
      ))}

      {problem && <ErrorNote>{te(problem)}</ErrorNote>}
      <div className="flex flex-col gap-3">
        <Button onClick={save} disabled={saving}>
          {saving ? t("saving") : t("save")}
        </Button>
        <ButtonLink href="/setup/members" variant="secondary">
          {tc("back")}
        </ButtonLink>
      </div>
    </SetupFrame>
  );
}
