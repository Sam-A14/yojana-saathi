"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { SetupFrame } from "@/components/SetupFrame";
import { Button, ChoiceGroup, ErrorNote, SelectField, TextField } from "@/components/ui";
import { api, errorKind } from "@/lib/api";
import { makeFamilyCode } from "@/lib/family-code";
import { AREA_TYPES, CATEGORIES, INCOME_BANDS } from "@/lib/options";
import { STATES } from "@/lib/states";
import { STEP_PATHS, forgetFamily, saveFamily, useStoredFamily } from "@/lib/storage";

export default function BasicsPage() {
  const t = useTranslations("basics");
  const to = useTranslations("options");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const { ready, family: existing } = useStoredFamily();

  // Most families live in Uttar Pradesh (the state this version covers), so start there.
  const [state, setState] = useState<string | null>("UP");
  const [district, setDistrict] = useState("");
  const [area, setArea] = useState<string | null>(null);
  const [income, setIncome] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<"network" | "denied" | "limit" | "generic" | null>(null);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setProblem(null);
    try {
      const created = await api.createHousehold({
        state,
        district: district.trim() || null,
        area_type: area,
        income_band: income,
        category,
      });
      // The token is returned only now and never again, so it is saved before anything else.
      const code = makeFamilyCode({ id: created.id, token: created.access_token });
      saveFamily(code, "code");
      router.push("/setup/code");
    } catch (error) {
      setProblem(errorKind(error));
      setSaving(false);
    }
  }

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

  return (
    <SetupFrame step={1}>
      <form onSubmit={create} className="flex flex-col gap-6">
        <h1 className="text-2xl font-bold">{t("title")}</h1>
        <p>{t("intro")}</p>
        <SelectField
          label={t("state")}
          value={state}
          onChange={setState}
          options={STATES.map((s) => ({ value: s.code, label: locale === "hi" ? s.hi : s.en }))}
          emptyLabel={tc("choose")}
        />
        <TextField label={t("district")} value={district} onChange={setDistrict} maxLength={60} />
        <ChoiceGroup
          legend={t("area")}
          options={AREA_TYPES.map((v) => ({ value: v, label: to(`area.${v}`) }))}
          value={area}
          onChange={setArea}
          notSureLabel={tc("notSure")}
        />
        <SelectField
          label={t("income")}
          hint={t("incomeHint")}
          value={income}
          onChange={setIncome}
          options={INCOME_BANDS.map((v) => ({ value: v, label: to(`income.${v}`) }))}
          emptyLabel={tc("notSure")}
        />
        <SelectField
          label={t("category")}
          hint={t("categoryHint")}
          value={category}
          onChange={setCategory}
          options={CATEGORIES.map((v) => ({ value: v, label: to(`category.${v}`) }))}
          emptyLabel={t("categoryNone")}
        />
        {problem && <ErrorNote>{te(problem)}</ErrorNote>}
        <Button type="submit" disabled={saving}>
          {saving ? t("saving") : tc("next")}
        </Button>
      </form>
    </SetupFrame>
  );
}
