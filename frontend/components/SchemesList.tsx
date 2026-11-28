"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { CategoryIcon, categoryKey } from "@/components/icons";
import { MySchemeLink } from "@/components/MySchemeLink";
import { SchemeCard } from "@/components/SchemeCard";
import { Button, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { GROUP_ORDER } from "@/lib/categories";
import { categoryWords } from "@/lib/myscheme";
import type { SchemeSummary } from "@/lib/types";


/** Every scheme in the catalogue, grouped by category. Public: no sign-in, no family data. Loaded in
 * the browser (see decision 018), so a sleeping backend never blocks the page itself. */
export function SchemesList() {
  const t = useTranslations("schemesPage");
  const tc = useTranslations("common");
  const tCategory = useTranslations("categories");
  const [state, setState] = useState<"loading" | "failed" | SchemeSummary[]>("loading");

  // Bumped by "Try again" to run the request again.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .listSchemes()
      .then((schemes) => !cancelled && setState(schemes))
      .catch(() => !cancelled && setState("failed"));
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  function retry() {
    setState("loading");
    setAttempt((count) => count + 1);
  }

  if (state === "loading") return <Skeleton label={t("loading")} />;
  if (state === "failed") {
    return (
      <div className="flex flex-col gap-4">
        <p role="alert" className="text-lg font-semibold">
          {t("failed")}
        </p>
        <Button onClick={retry}>{tc("retry")}</Button>
      </div>
    );
  }
  if (state.length === 0) return <p className="text-lg">{t("none")}</p>;

  return (
    <div className="flex flex-col gap-8">
      {GROUP_ORDER.map((group) => {
        const schemes = state.filter((scheme) => categoryKey(scheme.category) === group);
        if (schemes.length === 0) return null;
        const words = categoryWords(group, schemes.some((s) => s.level === "state"));
        return (
          <section key={group} aria-labelledby={`group-${group}`} className="flex flex-col gap-4">
            <h2 id={`group-${group}`} className="flex items-center gap-3 text-2xl font-extrabold">
              <CategoryIcon category={group} size={26} />
              {tCategory(group)}
            </h2>
            <ul className="grid gap-4 md:grid-cols-2">
              {schemes.map((scheme) => (
                <li key={scheme.slug}>
                  <SchemeCard scheme={scheme} showCategory={false} />
                </li>
              ))}
            </ul>
            {/* More schemes than the ones we check, for this topic (state schemes too, if we have one). */}
            {words.length > 0 && <MySchemeLink words={words} />}
          </section>
        );
      })}
      <MySchemeLink />
    </div>
  );
}
