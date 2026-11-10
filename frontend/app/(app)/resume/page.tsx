"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { type FormEvent, useId, useState } from "react";
import { Button, ButtonLink, ErrorNote } from "@/components/ui";
import { api, errorKind } from "@/lib/api";
import { makeFamilyCode, parseFamilyCode } from "@/lib/family-code";
import { saveFamily } from "@/lib/storage";

export default function ResumePage() {
  const t = useTranslations("resume");
  const te = useTranslations("errors");
  const router = useRouter();
  const inputId = useId();
  const [text, setText] = useState("");
  const [checking, setChecking] = useState(false);
  const [problem, setProblem] = useState<"invalid" | "network" | "denied" | "limit" | "generic" | null>(
    null,
  );

  async function open(event: FormEvent) {
    event.preventDefault();
    const family = parseFamilyCode(text);
    if (!family) {
      setProblem("invalid");
      return;
    }
    setProblem(null);
    setChecking(true);
    try {
      // The API answers 403 for a wrong code, and the same 403 for a household that does not exist.
      await api.getHousehold(family);
    } catch (error) {
      setProblem(errorKind(error));
      setChecking(false);
      return;
    }
    // Opened from a code means setup was done before; the dashboard shows what is there.
    saveFamily(makeFamilyCode(family), "done");
    // This page is kept (hidden) by Next.js. On a shared phone the next person must not find the
    // code in the box.
    setText("");
    setChecking(false);
    router.push("/dashboard");
  }

  return (
    <form onSubmit={open} className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p>{t("intro")}</p>
      <div className="flex flex-col gap-1">
        <label htmlFor={inputId} className="text-base font-semibold">
          {t("label")}
        </label>
        <textarea
          id={inputId}
          rows={4}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t("placeholder")}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          className="w-full rounded-lg border border-zinc-400 bg-transparent p-3 font-mono text-base break-all dark:border-zinc-600"
        />
      </div>
      {problem === "invalid" && <ErrorNote>{t("invalid")}</ErrorNote>}
      {problem && problem !== "invalid" && <ErrorNote>{te(problem)}</ErrorNote>}
      {checking && <p role="status">{t("checking")}</p>}
      <Button type="submit" disabled={checking || text.trim() === ""}>
        {t("submit")}
      </Button>
      <p className="text-base text-zinc-600 dark:text-zinc-400">{t("lost")}</p>
      <ButtonLink href="/setup/basics" variant="secondary">
        {t("startAgain")}
      </ButtonLink>
    </form>
  );
}
