"use client";

import { useEffect, useState } from "react";
import { SchemeCard } from "@/components/SchemeCard";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { SchemeSummary } from "@/lib/types";

/** Cards for the schemes in the catalogue (GET /schemes). Loaded in the browser, like the rest of
 * the app: the backend can take up to a minute to wake up, and the home page must not wait for it. */
export function SchemesWeCheck() {
  const t = useTranslations("landing");
  const [state, setState] = useState<"loading" | "failed" | SchemeSummary[]>("loading");

  useEffect(() => {
    let cancelled = false;
    api
      .listSchemes()
      .then((schemes) => !cancelled && setState(schemes))
      .catch(() => !cancelled && setState("failed"));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "loading") return <p role="status" className="min-h-40 text-lg text-muted">{t("schemesLoading")}</p>;
  if (state === "failed" || state.length === 0) return <p className="text-lg text-muted">{t("schemesFailed")}</p>;

  return (
    <ul className="grid gap-6 md:grid-cols-2">
      {state.map((scheme) => (
        <li key={scheme.slug}>
          <SchemeCard scheme={scheme} />
        </li>
      ))}
    </ul>
  );
}
