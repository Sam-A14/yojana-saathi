"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorKind, type ErrorKind } from "@/lib/api";
import { clearSession, type Session } from "@/lib/session";
import { Button, ErrorNote } from "./ui";

/**
 * Two different things, kept apart on purpose:
 *  - Delete my data: removes the person, their email and their family from our server for good
 *    (DELETE /me; the database cascades to members, papers and results), then clears this phone too.
 *  - Sign out: only ends the session on this phone (a shared phone is the normal case). Everything
 *    stays on the server and opens again by signing in with the same email.
 */
export function MyData({ session }: { session: Session }) {
  const t = useTranslations("privacy");
  const te = useTranslations("errors");
  const router = useRouter();
  const [panel, setPanel] = useState<"delete" | "signout" | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<ErrorKind | null>(null);

  function close() {
    setPanel(null);
    setProblem(null);
  }

  async function deleteEverything() {
    setBusy(true);
    setProblem(null);
    try {
      await api.deleteMe(session.token);
    } catch (error) {
      setProblem(errorKind(error));
      setBusy(false);
      return;
    }
    clearSession();
    router.push("/deleted");
  }

  async function signOut() {
    // Best effort: if the server cannot be reached, this phone still forgets the session.
    await api.signOut(session.token).catch(() => undefined);
    clearSession();
    router.push("/");
  }

  return (
    <section aria-labelledby="my-data" className="flex flex-col gap-4 border-t border-zinc-300 pt-6 dark:border-zinc-700">
      <h2 id="my-data" className="text-xl font-bold">
        {t("title")}
      </h2>
      <p>{t("intro")}</p>
      <p className="font-semibold">{t("signedInAs", { email: session.email })}</p>

      {panel === null && (
        <div className="flex flex-col gap-3">
          <Button variant="secondary" onClick={() => setPanel("signout")}>
            {t("signOutButton")}
          </Button>
          <Button variant="danger" onClick={() => setPanel("delete")}>
            {t("deleteButton")}
          </Button>
        </div>
      )}

      {panel === "delete" && (
        <div role="alertdialog" aria-labelledby="delete-title" aria-describedby="delete-warning" className="flex flex-col gap-3 rounded-lg border-2 border-red-700 p-4">
          <h3 id="delete-title" className="text-lg font-bold">{t("deleteTitle")}</h3>
          <p id="delete-warning">{t("deleteWarning")}</p>
          {problem && <ErrorNote>{te(problem)}</ErrorNote>}
          <Button variant="danger" onClick={deleteEverything} disabled={busy}>
            {busy ? t("deleting") : t("deleteYes")}
          </Button>
          <Button variant="secondary" onClick={close} disabled={busy}>
            {t("deleteNo")}
          </Button>
        </div>
      )}

      {panel === "signout" && (
        <div role="alertdialog" aria-labelledby="signout-title" aria-describedby="signout-warning" className="flex flex-col gap-3 rounded-lg border-2 border-amber-600 p-4">
          <h3 id="signout-title" className="text-lg font-bold">{t("signOutTitle")}</h3>
          <p id="signout-warning">{t("signOutWarning")}</p>
          <Button onClick={signOut}>{t("signOutYes")}</Button>
          <Button variant="secondary" onClick={close}>
            {t("signOutNo")}
          </Button>
        </div>
      )}
    </section>
  );
}
