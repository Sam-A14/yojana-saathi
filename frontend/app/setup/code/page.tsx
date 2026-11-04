"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { SetupFrame } from "@/components/SetupFrame";
import { Button } from "@/components/ui";
import { makeFamilyCode } from "@/lib/family-code";
import { advanceTo } from "@/lib/storage";
import type { Family } from "@/lib/types";
import { useSetupFamily } from "@/lib/use-setup-family";

function downloadTextFile(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// Keyed by the family: the "I have saved my code" tick belongs to one family's code, and a new family
// must not inherit it (tests/e2e/shared-phone.spec.ts fails without this).
export default function CodePage() {
  const family = useSetupFamily();
  const tc = useTranslations("common");
  if (!family) return <p>{tc("loading")}</p>;
  return <CodeScreen key={family.id} family={family} />;
}

function CodeScreen({ family }: { family: Family }) {
  const t = useTranslations("code");
  const tc = useTranslations("common");
  const router = useRouter();
  const [copy, setCopy] = useState<"idle" | "done" | "failed">("idle");
  const [saved, setSaved] = useState(false);

  const code = makeFamilyCode(family);

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopy("done");
    } catch {
      setCopy("failed"); // clipboard blocked: the code is selectable above for copying by hand
    }
  }

  function goOn() {
    advanceTo("members");
    router.push("/setup/members");
  }

  return (
    <SetupFrame step={2}>
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p className="hidden print:block">{t("printHeading")}</p>
      <p>{t("intro")}</p>
      <p className="rounded-lg border-2 border-emerald-700 p-4 font-mono text-base break-all select-all">
        {code}
      </p>
      <div role="note" className="rounded-lg border border-amber-500 bg-amber-50 p-4 text-amber-950 dark:bg-amber-950 dark:text-amber-100">
        <p className="font-bold">{t("warningTitle")}</p>
        <p>{t("warning")}</p>
      </div>
      <p className="hidden print:block">{t("printKeep")}</p>

      <div className="flex flex-col gap-3 print:hidden">
        <Button variant="secondary" onClick={copyCode}>
          {copy === "done" ? t("copied") : t("copy")}
        </Button>
        {copy === "failed" && <p role="alert">{t("copyFailed")}</p>}
        <Button
          variant="secondary"
          onClick={() => downloadTextFile("yojana-saathi-family-code.txt", t("file", { code }))}
        >
          {t("download")}
        </Button>
        <Button variant="secondary" onClick={() => window.print()}>
          {t("print")}
        </Button>
      </div>

      <label className="flex items-start gap-3 text-base print:hidden">
        <input
          type="checkbox"
          checked={saved}
          onChange={(event) => setSaved(event.target.checked)}
          className="mt-1 size-6 shrink-0"
        />
        <span>{t("saved")}</span>
      </label>
      <Button onClick={goOn} disabled={!saved} className="print:hidden">
        {tc("next")}
      </Button>
    </SetupFrame>
  );
}
