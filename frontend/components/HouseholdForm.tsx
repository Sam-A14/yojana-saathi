"use client";

import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";
import { AREA_TYPES, CATEGORIES, HOUSE_TYPES, INCOME_BANDS } from "@/lib/options";
import { STATES } from "@/lib/states";
import type { HouseholdFields } from "@/lib/types";
import { Button, ChoiceGroup, ErrorNote, SelectField, TextField, YesNoGroup } from "./ui";

export type HouseholdValues = {
  state: string | null;
  district: string;
  area: string | null;
  house: string | null; // no_house, kutcha or pucca; null = "Not sure"
  income: string | null;
  category: string | null;
  bpl: boolean | null; // null = "Not sure": saved as null, which means unknown, never "no"
};

/**
 * The seven questions about a home. Used twice: to set up a new family (Basics) and to change the
 * answers later (Edit household details). It only collects answers; the caller saves them.
 */
export function HouseholdForm({
  initial,
  submitLabel,
  savingLabel,
  saving,
  problem,
  onSubmit,
}: {
  initial: HouseholdValues;
  submitLabel: string;
  savingLabel: string;
  saving: boolean;
  problem: string | null;
  onSubmit: (data: HouseholdFields) => void;
}) {
  const t = useTranslations("basics");
  const to = useTranslations("options");
  const tc = useTranslations("common");
  const yesNo = { yes: tc("yes"), no: tc("no"), notSure: tc("notSure") };
  const locale = useLocale();

  const [state, setState] = useState(initial.state);
  const [district, setDistrict] = useState(initial.district);
  const [area, setArea] = useState(initial.area);
  const [house, setHouse] = useState(initial.house);
  const [income, setIncome] = useState(initial.income);
  const [category, setCategory] = useState(initial.category);
  const [bpl, setBpl] = useState(initial.bpl);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      state,
      district: district.trim() || null,
      area_type: area,
      house_type: house,
      income_band: income,
      category,
      is_bpl: bpl,
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
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
      <ChoiceGroup
        legend={t("house")}
        hint={t("houseHint")}
        options={HOUSE_TYPES.map((v) => ({ value: v, label: to(`house.${v}`) }))}
        value={house}
        onChange={setHouse}
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
      <YesNoGroup legend={t("bpl")} hint={t("bplHint")} value={bpl} onChange={setBpl} labels={yesNo} />
      <SelectField
        label={t("category")}
        hint={t("categoryHint")}
        value={category}
        onChange={setCategory}
        options={CATEGORIES.map((v) => ({ value: v, label: to(`category.${v}`) }))}
        emptyLabel={t("categoryNone")}
      />
      {problem && <ErrorNote>{problem}</ErrorNote>}
      <Button type="submit" disabled={saving}>
        {saving ? savingLabel : submitLabel}
      </Button>
    </form>
  );
}
