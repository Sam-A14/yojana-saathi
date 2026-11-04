"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { SetupFrame } from "@/components/SetupFrame";
import { HouseholdForm } from "@/components/HouseholdForm";
import { Button } from "@/components/ui";
import { api, errorKind } from "@/lib/api";
import { makeFamilyCode } from "@/lib/family-code";
import { STEP_PATHS, forgetFamily, saveFamily, useStoredFamily } from "@/lib/storage";
import type { HouseholdFields } from "@/lib/types";

// The form is a child that exists only while there is no saved family, so what was typed for one
// family is gone when the next one starts. Without this the previous family's district, area and
// income came back in the new form (tests/e2e/shared-phone.spec.ts fails without it).
export default function BasicsPage() {
  const t = useTranslations("basics");
  const tc = useTranslations("common");
  const router = useRouter();
  const { ready, family: existing } = useStoredFamily();

  if (!ready) return <p>{tc("loading")}</p>;

  // Starting again would replace the saved code on this phone, so ask first.
  if (existing) {
    return (
      <SetupFrame step={1}>
        <h1 className="text-2xl font-bold">{t("existingTitle")}</h1>
        <div className="flex flex-col gap-3">
          <Button onClick={() => router.push(STEP_PATHS[existing.step])}>{t("existingContinue")}</Button>
          <Button variant="secondary" onClick={forgetFamily}>
            {t("existingNew")}
          </Button>
          <p className="text-base text-zinc-600 dark:text-zinc-400">{t("existingNewNote")}</p>
        </div>
      </SetupFrame>
    );
  }

  return <BasicsForm />;
}

function BasicsForm() {
  const t = useTranslations("basics");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<"network" | "denied" | "limit" | "generic" | null>(null);

  async function create(data: HouseholdFields) {
    setSaving(true);
    setProblem(null);
    try {
      const created = await api.createHousehold(data);
      // The token is returned only now and never again, so it is saved before anything else.
      const code = makeFamilyCode({ id: created.id, token: created.access_token });
      saveFamily(code, "code");
      router.push("/setup/code");
    } catch (error) {
      setProblem(errorKind(error));
      setSaving(false);
    }
  }

  return (
    <SetupFrame step={1}>
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p>{t("intro")}</p>
        <HouseholdForm
          // Most families live in Uttar Pradesh (the state this version covers), so start there.
          initial={{ state: "UP", district: "", area: null, income: null, category: null }}
          submitLabel={tc("next")}
          savingLabel={t("saving")}
          saving={saving}
          problem={problem && te(problem)}
          onSubmit={create}
        />
      </div>
    </SetupFrame>
  );
}
