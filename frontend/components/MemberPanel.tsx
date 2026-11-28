"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { api, errorKind, type ErrorKind } from "@/lib/api";
import type { Family, Member, MemberInput } from "@/lib/types";
import { MemberForm } from "./MemberForm";

/** The add-a-person and edit-a-person screen of the dashboard. It is the same form and the same API
 * calls as step 2 of the setup (MemberForm, addMember, updateMember); only what happens after is
 * different: the dashboard is told, and shows the family's results again. */
export function MemberPanel({
  family,
  member,
  onDone,
  onCancel,
}: {
  family: Family;
  /** null = a new person. */
  member: Member | null;
  onDone: (saved: Member, wasNew: boolean) => void;
  onCancel: () => void;
}) {
  const te = useTranslations("errors");
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<ErrorKind | null>(null);

  async function save(data: MemberInput) {
    setSaving(true);
    setProblem(null);
    try {
      const saved = member
        ? await api.updateMember(family, member.id, data)
        : await api.addMember(family, data);
      onDone(saved, member === null);
    } catch (error) {
      setProblem(errorKind(error));
    }
    setSaving(false);
  }

  return (
    <MemberForm
      // A new form for each person, so one person's answers never carry over to the next.
      key={member?.id ?? "new"}
      member={member}
      defaultRelation={null}
      saving={saving}
      problem={problem ? te(problem) : null}
      onSave={save}
      onCancel={onCancel}
    />
  );
}
