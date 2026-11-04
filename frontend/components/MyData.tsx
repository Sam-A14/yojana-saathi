"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorKind } from "@/lib/api";
import { forgetFamily } from "@/lib/storage";
import type { Family } from "@/lib/types";
import { Button, ErrorNote } from "./ui";

/**
 * Two different things, kept apart on purpose:
 *  - Delete my data: removes the family from our server for good (the API cascades to members,
 *    papers and results), then clears this phone too.
 *  - Forget this device: only clears the family code from this phone (a shared phone is the normal
 *    case). The family stays on the server and opens again with the code.
 */
export function MyData({ family }: { family: Family }) {
  const t = useTranslations("privacy");
  const te = useTranslations("errors");
  const router = useRouter();
  const [panel, setPanel] = useState<"delete" | "forget" | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<"network" | "denied" | "limit" | "generic" | null>(null);

  function close() {
    setPanel(null);
    setProblem(null);
  }

  async function deleteEverything() {
    setBusy(true);
    setProblem(null);
    try {
      await api.deleteHousehold(family);
    } catch (error) {
      setProblem(errorKind(error));
      setBusy(false);
      return;
    }
    forgetFamily();
    router.push("/deleted");
  }

  function forgetDevice() {
    forgetFamily();
    router.push("/");
  }

  return (
    <section aria-labelledby="my-data" className="flex flex-col gap-4 border-t border-zinc-300 pt-6 dark:border-zinc-700">
      <h2 id="my-data" className="text-xl font-bold">
        {t("title")}
      </h2>
      <p>{t("intro")}</p>

      {panel === null && (
        <div className="flex flex-col gap-3">
          <Button variant="secondary" onClick={() => setPanel("forget")}>
            {t("forgetButton")}
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

      {panel === "forget" && (
        <div role="alertdialog" aria-labelledby="forget-title" aria-describedby="forget-warning" className="flex flex-col gap-3 rounded-lg border-2 border-amber-600 p-4">
          <h3 id="forget-title" className="text-lg font-bold">{t("forgetTitle")}</h3>
          <p id="forget-warning">{t("forgetWarning")}</p>
          <p className="font-semibold">{t("forgetReminder")}</p>
          <Button onClick={forgetDevice}>{t("forgetYes")}</Button>
          <Button variant="secondary" onClick={close}>
            {t("forgetNo")}
          </Button>
        </div>
      )}
    </section>
  );
}
