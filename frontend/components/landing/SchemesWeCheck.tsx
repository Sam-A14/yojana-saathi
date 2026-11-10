"use client";

import { ExternalLink } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { CategoryIcon, categoryKey } from "@/components/icons";
import { Card, buttonClass } from "@/components/ui";
import { VerificationLabel } from "@/components/VerificationLabel";
import { api } from "@/lib/api";
import { benefitText, schemeName } from "@/lib/format";
import type { SchemeSummary } from "@/lib/types";

/** Cards for the schemes in the catalogue (GET /schemes). Loaded in the browser, like the rest of
 * the app: the backend can take up to a minute to wake up, and the home page must not wait for it. */
export function SchemesWeCheck() {
  const t = useTranslations("landing");
  const tCategory = useTranslations("categories");
  const locale = useLocale() === "hi" ? "hi" : "en";
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
      {state.map((scheme) => {
        const benefit = benefitText(scheme, locale);
        return (
          <li key={scheme.slug}>
            <Card className="flex h-full flex-col gap-4 transition duration-200 hover:-translate-y-1 hover:shadow-lift">
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                  <CategoryIcon category={scheme.category} size={26} />
                </span>
                <span className="text-lg font-bold text-primary">
                  {tCategory(categoryKey(scheme.category))}
                </span>
              </div>
              <h3 className="text-xl font-bold">{schemeName(scheme, locale)}</h3>
              {benefit && <p className="text-base text-muted">{benefit}</p>}
              <div className="mt-auto flex flex-col items-start gap-3">
                <VerificationLabel scheme={scheme} />
                <a
                  href={scheme.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClass("secondary", "w-full sm:w-auto")}
                >
                  {t("officialSite")}
                  <ExternalLink size={20} />
                </a>
              </div>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}
