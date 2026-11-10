"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { SetupFrame } from "@/components/SetupFrame";
import { Button, ButtonLink, ChoiceGroup, ErrorNote, YesNoGroup } from "@/components/ui";
import { api, errorKind, type ErrorKind } from "@/lib/api";
import { GOVT_EMPLOYEE, PENSION_BANDS } from "@/lib/options";
import type { Member } from "@/lib/types";
import { useSetupFamily } from "@/lib/use-setup-family";

const ADULT_AGE = 18;

// The five PM-KISAN exclusion facts for one person. null = not sure.
type Answers = {
  paid_income_tax_last_year: boolean | null;
  govt_employee: string | null;
  pension_band: string | null;
  is_registered_professional: boolean | null;
  holds_constitutional_post: boolean | null;
};

type Loaded = { adults: Member[]; answers: Record<string, Answers> };

function startingAnswers(adults: Member[]): Record<string, Answers> {
  return Object.fromEntries(
    adults.map((m) => [
      m.id,
      {
        paid_income_tax_last_year: m.paid_income_tax_last_year,
        govt_employee: m.govt_employee,
        pension_band: m.pension_band,
        is_registered_professional: m.is_registered_professional,
        holds_constitutional_post: m.holds_constitutional_post,
      },
    ]),
  );
}

export default function ExclusionsPage() {
  const t = useTranslations("exclusions");
  const to = useTranslations("options");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const router = useRouter();
  const family = useSetupFamily();

  const [data, setData] = useState<Loaded | null>(null);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<ErrorKind | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    api
      .listMembers(family)
      .then((members) => {
        if (cancelled) return;
        const thisYear = new Date().getFullYear();
        // Someone with no birth year is asked too: skipping them could hide a real exclusion.
        const adults = members.filter((m) => m.birth_year === null || thisYear - m.birth_year >= ADULT_AGE);
        setData({ adults, answers: startingAnswers(adults) });
      })
      .catch((error) => {
        if (!cancelled) setProblem(errorKind(error));
      });
    return () => {
      cancelled = true;
    };
  }, [family]);

  async function finish() {
    if (!family || !data) return;
    setSaving(true);
    setProblem(null);
    try {
      // PATCH sends only these five facts, so nothing else about the person is touched.
      await Promise.all(data.adults.map((m) => api.updateMember(family, m.id, data.answers[m.id])));
    } catch (error) {
      setProblem(errorKind(error));
      setSaving(false);
      return;
    }
    router.push("/dashboard");
  }

  if (!data) return problem ? <ErrorNote>{te(problem)}</ErrorNote> : <p>{tc("loading")}</p>;

  const labels = { yes: tc("yes"), no: tc("no"), notSure: tc("notSure") };
  function set<K extends keyof Answers>(id: string, key: K, value: Answers[K]) {
    setData((current) =>
      current && { ...current, answers: { ...current.answers, [id]: { ...current.answers[id], [key]: value } } },
    );
  }

  return (
    <SetupFrame step={4}>
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p>{t("intro")}</p>
      {data.adults.length === 0 && <p>{t("noAdults")}</p>}

      {data.adults.map((member) => {
        const a = data.answers[member.id];
        return (
          <section
            key={member.id}
            aria-labelledby={`adult-${member.id}`}
            className="flex flex-col gap-6 rounded-lg border border-zinc-300 p-4 dark:border-zinc-700"
          >
            <h2 id={`adult-${member.id}`} className="text-xl font-bold">
              {t("forName", { name: member.nickname })}
            </h2>
            <YesNoGroup
              legend={t("tax")}
              value={a.paid_income_tax_last_year}
              labels={labels}
              onChange={(v) => set(member.id, "paid_income_tax_last_year", v)}
            />
            <ChoiceGroup
              legend={t("govt")}
              options={GOVT_EMPLOYEE.map((v) => ({ value: v, label: to(`govt.${v}`) }))}
              value={a.govt_employee}
              notSureLabel={tc("notSure")}
              onChange={(v) => set(member.id, "govt_employee", v)}
            />
            <ChoiceGroup
              legend={t("pension")}
              options={PENSION_BANDS.map((v) => ({ value: v, label: to(`pension.${v}`) }))}
              value={a.pension_band}
              notSureLabel={tc("notSure")}
              onChange={(v) => set(member.id, "pension_band", v)}
            />
            <YesNoGroup
              legend={t("professional")}
              value={a.is_registered_professional}
              labels={labels}
              onChange={(v) => set(member.id, "is_registered_professional", v)}
            />
            <YesNoGroup
              legend={t("post")}
              value={a.holds_constitutional_post}
              labels={labels}
              onChange={(v) => set(member.id, "holds_constitutional_post", v)}
            />
          </section>
        );
      })}

      {problem && <ErrorNote>{te(problem)}</ErrorNote>}
      <div className="flex flex-col gap-3">
        <Button onClick={finish} disabled={saving}>
          {saving ? t("saving") : t("finish")}
        </Button>
        <ButtonLink href="/setup/documents" variant="secondary">
          {tc("back")}
        </ButtonLink>
      </div>
    </SetupFrame>
  );
}
