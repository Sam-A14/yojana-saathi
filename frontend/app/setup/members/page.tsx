"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MemberForm } from "@/components/MemberForm";
import { SetupFrame } from "@/components/SetupFrame";
import { Button, ButtonLink, ErrorNote } from "@/components/ui";
import { api, errorKind } from "@/lib/api";
import { isRelation } from "@/lib/options";
import { advanceTo } from "@/lib/storage";
import type { Member, MemberInput } from "@/lib/types";
import { useSetupFamily } from "@/lib/use-setup-family";

const MAX_MEMBERS = 20; // the same limit the API enforces

type Problem = "network" | "denied" | "limit" | "generic";

export default function MembersPage() {
  const t = useTranslations("members");
  const to = useTranslations("options");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const router = useRouter();
  const family = useSetupFamily();

  const [members, setMembers] = useState<Member[] | null>(null);
  // null: showing the list. "new": the add form. A member: editing that person.
  const [editing, setEditing] = useState<Member | "new" | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [needOne, setNeedOne] = useState(false);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    api
      .listMembers(family)
      .then((loaded) => {
        if (cancelled) return;
        setMembers(loaded);
        // Nobody yet: go straight to the form for the first person.
        if (loaded.length === 0) setEditing("new");
      })
      .catch((error) => {
        if (!cancelled) setProblem(errorKind(error));
      });
    return () => {
      cancelled = true;
    };
  }, [family]);

  async function save(data: MemberInput) {
    if (!family || !members) return;
    setSaving(true);
    setProblem(null);
    try {
      if (editing === "new") {
        const added = await api.addMember(family, data);
        setMembers([...members, added]);
      } else if (editing) {
        const updated = await api.updateMember(family, editing.id, data);
        setMembers(members.map((m) => (m.id === updated.id ? updated : m)));
      }
      setEditing(null);
      setNeedOne(false);
    } catch (error) {
      setProblem(errorKind(error));
    }
    setSaving(false);
  }

  async function remove(member: Member) {
    if (!family || !members) return;
    setProblem(null);
    try {
      await api.deleteMember(family, member.id);
      setMembers(members.filter((m) => m.id !== member.id));
      setRemoving(null);
    } catch (error) {
      setProblem(errorKind(error));
    }
  }

  function goOn() {
    if (!members || members.length === 0) {
      setNeedOne(true);
      return;
    }
    advanceTo("documents");
    router.push("/setup/documents");
  }

  if (!members) {
    return problem ? <ErrorNote>{te(problem)}</ErrorNote> : <p>{tc("loading")}</p>;
  }

  if (editing) {
    return (
      <SetupFrame step={3}>
        <MemberForm
          // A new form for each person, so one person's answers never carry over to the next.
          key={editing === "new" ? "new" : editing.id}
          member={editing === "new" ? null : editing}
          defaultRelation={members.length === 0 ? "self" : null}
          saving={saving}
          problem={problem ? te(problem) : null}
          onSave={save}
          onCancel={() => {
            setEditing(null);
            setProblem(null);
          }}
        />
      </SetupFrame>
    );
  }

  const full = members.length >= MAX_MEMBERS;
  return (
    <SetupFrame step={3}>
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p>{t("intro")}</p>

      {members.length === 0 && <p>{t("addFirst")}</p>}
      <ul className="flex flex-col gap-3">
        {members.map((member) => (
          <li key={member.id} className="rounded-lg border border-zinc-300 p-4 dark:border-zinc-700">
            <p className="text-lg font-semibold">{member.nickname}</p>
            <p className="text-zinc-600 dark:text-zinc-400">
              {isRelation(member.relation) ? to(`relation.${member.relation}`) : member.relation}
              {member.birth_year ? ` · ${t("bornIn", { year: member.birth_year })}` : ""}
            </p>
            {removing === member.id ? (
              <div className="mt-3 flex flex-col gap-2">
                <p>{t("removeConfirm", { name: member.nickname })}</p>
                <Button variant="danger" onClick={() => remove(member)}>
                  {t("removeYes")}
                </Button>
                <Button variant="secondary" onClick={() => setRemoving(null)}>
                  {t("removeKeep")}
                </Button>
              </div>
            ) : (
              <div className="mt-3 flex gap-2">
                <Button variant="secondary" onClick={() => setEditing(member)} aria-label={`${t("edit")}: ${member.nickname}`}>
                  {t("edit")}
                </Button>
                <Button variant="secondary" onClick={() => setRemoving(member.id)} aria-label={`${t("remove")}: ${member.nickname}`}>
                  {t("remove")}
                </Button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {full ? (
        <p>{t("limitReached")}</p>
      ) : (
        <Button variant="secondary" onClick={() => setEditing("new")}>
          {t("add")}
        </Button>
      )}

      {needOne && <ErrorNote>{t("needOne")}</ErrorNote>}
      {problem && <ErrorNote>{te(problem)}</ErrorNote>}
      <div className="flex flex-col gap-3">
        <Button onClick={goOn}>{tc("next")}</Button>
        <ButtonLink href="/setup/code" variant="secondary">
          {tc("back")}
        </ButtonLink>
      </div>
    </SetupFrame>
  );
}
