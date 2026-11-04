"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";
import {
  EDUCATIONS,
  GENDERS,
  MARITAL_STATUSES,
  OCCUPATIONS,
  RELATIONS,
} from "@/lib/options";
import type { Member, MemberInput } from "@/lib/types";
import { Button, ChoiceGroup, ErrorNote, SelectField, TextField, YesNoGroup } from "./ui";

const FIRST_BIRTH_YEAR = 1900;

/** One person's details. Everything except name and relation can be left as "not sure". */
export function MemberForm({
  member,
  defaultRelation,
  saving,
  problem,
  onSave,
  onCancel,
}: {
  member: Member | null;
  defaultRelation: string | null;
  saving: boolean;
  problem: string | null;
  onSave: (data: MemberInput) => void;
  onCancel: () => void;
}) {
  const t = useTranslations("members");
  const to = useTranslations("options");
  const tc = useTranslations("common");
  const yesNo = { yes: tc("yes"), no: tc("no"), notSure: tc("notSure") };

  const [nickname, setNickname] = useState(member?.nickname ?? "");
  const [relation, setRelation] = useState<string | null>(member?.relation ?? defaultRelation);
  const [birthYear, setBirthYear] = useState(member?.birth_year?.toString() ?? "");
  const [gender, setGender] = useState(member?.gender ?? null);
  const [marital, setMarital] = useState(member?.marital_status ?? null);
  const [occupation, setOccupation] = useState(member?.occupation ?? null);
  const [education, setEducation] = useState(member?.education ?? null);
  const [student, setStudent] = useState(member?.is_student ?? null);
  const [disability, setDisability] = useState(member?.disability ?? null);
  const [land, setLand] = useState(member?.owns_cultivable_land ?? null);
  const [remarried, setRemarried] = useState(member?.is_remarried ?? null);
  const [errors, setErrors] = useState<{ nickname?: string; relation?: string; birthYear?: string }>({});

  function submit(event: FormEvent) {
    event.preventDefault();
    // The current year is read here, when the button is pressed, not while the page is drawn.
    const maxYear = new Date().getFullYear();
    const year = birthYear.trim() === "" ? null : Number(birthYear.trim());
    const found: typeof errors = {};
    if (nickname.trim() === "") found.nickname = t("nicknameRequired");
    if (!relation) found.relation = t("relationRequired");
    if (year !== null && !(Number.isInteger(year) && year >= FIRST_BIRTH_YEAR && year <= maxYear)) {
      found.birthYear = t("birthYearError", { max: maxYear });
    }
    setErrors(found);
    if (Object.keys(found).length > 0 || !relation) return;

    onSave({
      nickname: nickname.trim(),
      relation,
      birth_year: year,
      gender,
      marital_status: marital,
      occupation,
      education,
      is_student: student,
      disability,
      owns_cultivable_land: land,
      // Only asked of widows; clear it if the person is no longer one, so no stale answer stays.
      is_remarried: marital === "widow" ? remarried : null,
    });
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-6" noValidate>
      <h2 className="text-xl font-bold">
        {member ? t("formTitleEdit", { name: member.nickname }) : t("formTitleNew")}
      </h2>
      <TextField
        label={t("nickname")}
        hint={t("nicknameHint")}
        error={errors.nickname}
        value={nickname}
        onChange={setNickname}
        maxLength={50}
        autoComplete="off"
      />
      <SelectField
        label={t("relation")}
        error={errors.relation}
        value={relation}
        onChange={setRelation}
        options={RELATIONS.map((v) => ({ value: v, label: to(`relation.${v}`) }))}
        emptyLabel={tc("choose")}
      />
      <TextField
        label={t("birthYear")}
        hint={t("birthYearHint")}
        error={errors.birthYear}
        value={birthYear}
        onChange={setBirthYear}
        inputMode="numeric"
        maxLength={4}
        autoComplete="off"
      />
      <ChoiceGroup
        legend={t("gender")}
        options={GENDERS.map((v) => ({ value: v, label: to(`gender.${v}`) }))}
        value={gender}
        onChange={setGender}
        notSureLabel={tc("notSure")}
      />
      <SelectField
        label={t("marital")}
        value={marital}
        onChange={setMarital}
        options={MARITAL_STATUSES.map((v) => ({ value: v, label: to(`marital.${v}`) }))}
        emptyLabel={tc("notSure")}
      />
      {marital === "widow" && (
        <YesNoGroup legend={t("remarried")} value={remarried} onChange={setRemarried} labels={yesNo} />
      )}
      <SelectField
        label={t("occupation")}
        value={occupation}
        onChange={setOccupation}
        options={OCCUPATIONS.map((v) => ({ value: v, label: to(`occupation.${v}`) }))}
        emptyLabel={tc("notSure")}
      />
      <SelectField
        label={t("education")}
        value={education}
        onChange={setEducation}
        options={EDUCATIONS.map((v) => ({ value: v, label: to(`education.${v}`) }))}
        emptyLabel={tc("notSure")}
      />
      <YesNoGroup legend={t("student")} value={student} onChange={setStudent} labels={yesNo} />
      <YesNoGroup legend={t("disability")} value={disability} onChange={setDisability} labels={yesNo} />
      <YesNoGroup legend={t("land")} value={land} onChange={setLand} labels={yesNo} />
      {problem && <ErrorNote>{problem}</ErrorNote>}
      <div className="flex flex-col gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? t("saving") : t("saveMember")}
        </Button>
        <Button variant="secondary" onClick={onCancel} disabled={saving}>
          {tc("cancel")}
        </Button>
      </div>
    </form>
  );
}
