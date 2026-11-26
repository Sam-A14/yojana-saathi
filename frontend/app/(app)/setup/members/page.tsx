"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MemberForm } from "@/components/MemberForm";
import { SetupFrame } from "@/components/SetupFrame";
import { Avatar } from "@/components/Avatar";
import { Button, ButtonLink, Card, ErrorNote, Skeleton } from "@/components/ui";
import { api, errorKind, type ErrorKind } from "@/lib/api";
import { isRelation } from "@/lib/options";
import type { Member, MemberInput } from "@/lib/types";
import { useSetupFamily } from "@/lib/use-setup-family";

const MAX_MEMBERS = 20; // the same limit the API enforces

type Problem = ErrorKind;

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
    router.push("/setup/documents");
  }

  if (!members) {
    return problem ? <ErrorNote>{te(problem)}</ErrorNote> : <Skeleton label={tc("loading")} />;
  }

  if (editing) {
    return (
      <SetupFrame step={2}>
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
    <SetupFrame step={2}>
      <h1 className="display text-3xl">{t("title")}</h1>
      <p className="text-lg">{t("intro")}</p>

      {members.length === 0 && <p>{t("addFirst")}</p>}
      <ul className="flex flex-col gap-3">
        {members.map((member) => (
          <li key={member.id}>
            <Card className="flex flex-col gap-4">
              <div className="flex items-center gap-4">
                <Avatar name={member.nickname} size="lg" />
                <div className="min-w-0">
                  <p className="break-words text-xl font-bold">{member.nickname}</p>
                  <p className="text-base text-muted">
                    {isRelation(member.relation) ? to(`relation.${member.relation}`) : member.relation}
                    {member.birth_year ? ` · ${t("bornIn", { year: member.birth_year })}` : ""}
                  </p>
                </div>
              </div>
              {removing === member.id ? (
                <div className="flex flex-col gap-3">
                  <p>{t("removeConfirm", { name: member.nickname })}</p>
                  <Button variant="danger" onClick={() => remove(member)}>
                    {t("removeYes")}
                  </Button>
                  <Button variant="secondary" onClick={() => setRemoving(null)}>
                    {t("removeKeep")}
                  </Button>
                </div>
              ) : (
                <div className="flex gap-3">
                  <Button variant="secondary" className="flex-1" onClick={() => setEditing(member)} aria-label={`${t("edit")}: ${member.nickname}`}>
                    {t("edit")}
                  </Button>
                  <Button variant="secondary" className="flex-1" onClick={() => setRemoving(member.id)} aria-label={`${t("remove")}: ${member.nickname}`}>
                    {t("remove")}
                  </Button>
                </div>
              )}
            </Card>
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
        {/* The home answers are saved already, so Back is the edit screen (not the first-step form, which only creates). */}
        <ButtonLink href="/household/edit" variant="secondary">
          {tc("back")}
        </ButtonLink>
      </div>
    </SetupFrame>
  );
}
