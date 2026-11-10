"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { HouseholdForm } from "@/components/HouseholdForm";
import { Button, ButtonLink, ErrorNote } from "@/components/ui";
import { api, errorKind } from "@/lib/api";
import type { Family, Household, HouseholdFields } from "@/lib/types";
import { useFamily } from "@/lib/use-family";

type Problem = "network" | "denied" | "limit" | "generic";

// Keyed by the family so this form can never carry one family's answers into another's.
// (A precaution: no test fails without it. See docs/decisions/016.)
export default function EditHouseholdPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const { ready, family } = useFamily();

  if (!ready) return <p role="status">{tc("loading")}</p>;
  if (!family) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-2xl font-bold">{t("none")}</h1>
        <ButtonLink href="/resume">{t("toResume")}</ButtonLink>
      </div>
    );
  }
  return <HouseholdEditor key={family.id} family={family} />;
}

function HouseholdEditor({ family }: { family: Family }) {
  const t = useTranslations("household");
  const td = useTranslations("dashboard");
  const te = useTranslations("errors");
  const router = useRouter();
  const [household, setHousehold] = useState<Household | null>(null);
  const [loadProblem, setLoadProblem] = useState<Problem | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getHousehold(family)
      .then((loaded) => {
        if (!cancelled) setHousehold(loaded);
      })
      .catch((error) => {
        if (!cancelled) setLoadProblem(errorKind(error));
      });
    return () => {
      cancelled = true;
    };
  }, [family, attempt]);

  async function save(data: HouseholdFields) {
    setSaving(true);
    setProblem(null);
    try {
      await api.updateHousehold(family, data);
    } catch (error) {
      setProblem(errorKind(error));
      setSaving(false);
      return;
    }
    // The dashboard asks for its results again when it opens, so the new answers show up there.
    router.push("/dashboard");
  }

  if (loadProblem) {
    return (
      <div className="flex flex-col gap-4">
        <ErrorNote>{te(loadProblem)}</ErrorNote>
        <Button
          onClick={() => {
            setLoadProblem(null);
            setAttempt((n) => n + 1);
          }}
        >
          {td("retry")}
        </Button>
      </div>
    );
  }
  if (!household) return <p role="status">{t("loading")}</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p>{t("intro")}</p>
      <HouseholdForm
        initial={{
          state: household.state,
          district: household.district ?? "",
          area: household.area_type,
          income: household.income_band,
          category: household.category,
        }}
        submitLabel={t("save")}
        savingLabel={t("saving")}
        saving={saving}
        problem={problem && te(problem)}
        onSubmit={save}
      />
      <ButtonLink href="/dashboard" variant="secondary">
        {t("cancel")}
      </ButtonLink>
    </div>
  );
}

