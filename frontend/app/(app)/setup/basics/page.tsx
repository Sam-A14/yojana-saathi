"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { SetupFrame } from "@/components/SetupFrame";
import { HouseholdForm } from "@/components/HouseholdForm";
import { type ErrorKind, api, errorKind } from "@/lib/api";
import { nextPathFor } from "@/lib/next-path";
import { type Session, setHouseholdId, useSession } from "@/lib/session";
import type { HouseholdFields } from "@/lib/types";

// The form is a child that exists only for a signed-in person with no household yet, so what was
// typed for one person is gone when the next one signs in. Without this the previous family's
// district, area and income came back in the new form (tests/e2e/shared-phone.spec.ts fails without it).
export default function BasicsPage() {
  const tc = useTranslations("common");
  const router = useRouter();
  const { ready, session } = useSession();

  useEffect(() => {
    if (!ready) return;
    if (!session) {
      router.replace("/signin");
      return;
    }
    // Already has a household (for example, signed in on a second phone): carry on from where the
    // server says they are.
    if (session.householdId) {
      nextPathFor(session)
        .then((path) => router.replace(path))
        .catch(() => router.replace("/dashboard"));
    }
  }, [ready, session, router]);

  if (!ready || !session || session.householdId) return <p>{tc("loading")}</p>;
  return <BasicsForm key={session.token} session={session} />;
}

function BasicsForm({ session }: { session: Session }) {
  const t = useTranslations("basics");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<ErrorKind | null>(null);

  async function create(data: HouseholdFields) {
    setSaving(true);
    setProblem(null);
    try {
      const created = await api.createHousehold(session.token, data);
      setHouseholdId(created.id);
      router.push("/setup/members");
    } catch (error) {
      // 409: this person already has a household (made on another phone while this form was open).
      if (errorKind(error) === "limit") {
        router.replace(await nextPathFor(session).catch(() => "/dashboard"));
        return;
      }
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
