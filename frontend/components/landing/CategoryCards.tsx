"use client";

import { ArrowRight, GraduationCap, HandHeart, HeartPulse, House, Armchair, Wheat, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SchemeSummary } from "@/lib/types";

// Each card is a TOPIC the family thinks in. `category` is the value the backend stores on a scheme
// (GET /schemes). A topic with no backend category yet (null) always reads "Coming soon": we never
// invent a count or a scheme for it. Healthcare and Families get a category when schemes for them
// are added to data/schemes_seed.
const CARDS: {
  key: "Education" | "Agriculture" | "Healthcare" | "Women" | "Seniors" | "Families";
  category: string | null;
  Icon: LucideIcon;
  tone: 1 | 2 | 3 | 4 | 5 | 6;
}[] = [
  { key: "Education", category: "student", Icon: GraduationCap, tone: 1 },
  { key: "Agriculture", category: "farmer", Icon: Wheat, tone: 2 },
  { key: "Healthcare", category: null, Icon: HeartPulse, tone: 3 },
  { key: "Women", category: "widow_pension", Icon: HandHeart, tone: 4 },
  { key: "Seniors", category: "pension", Icon: Armchair, tone: 5 },
  { key: "Families", category: null, Icon: House, tone: 6 },
];

// The pastel pairs are tokens (globals.css), written out here so Tailwind can see every class name.
const TONE = {
  1: "bg-cat1-bg text-cat1-fg",
  2: "bg-cat2-bg text-cat2-fg",
  3: "bg-cat3-bg text-cat3-fg",
  4: "bg-cat4-bg text-cat4-fg",
  5: "bg-cat5-bg text-cat5-fg",
  6: "bg-cat6-bg text-cat6-fg",
} as const;

/** The six topic cards. The number on each card is the real count from GET /schemes, loaded in the
 * browser like the rest of the app (a sleeping backend must not hold up the home page). A card with
 * no schemes says "Coming soon" and is not a link, so nobody lands on an empty page. */
export function CategoryCards() {
  const t = useTranslations("landing");
  const [schemes, setSchemes] = useState<"loading" | "failed" | SchemeSummary[]>("loading");

  useEffect(() => {
    let cancelled = false;
    api
      .listSchemes()
      .then((list) => !cancelled && setSchemes(list))
      .catch(() => !cancelled && setSchemes("failed"));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <ul aria-label={t("categoriesLabel")} className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(({ key, category, Icon, tone }) => {
          const count =
            schemes === "loading" || schemes === "failed" || category === null
              ? null
              : schemes.filter((scheme) => scheme.category === category).length;
          const linked = count !== null && count > 0 && category !== null;

          const body = (
            <>
              <span className="flex items-center gap-4">
                <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-surface/70`}>
                  <Icon aria-hidden size={30} />
                </span>
                <h3 className="text-xl font-extrabold">{t(`cat${key}`)}</h3>
              </span>
              <span className="text-lg">{t(`cat${key}Body`)}</span>
              {/* min-h keeps the card the same height while the count is still loading. */}
              <span className="mt-auto flex min-h-10 items-center justify-between gap-3">
                {schemes === "loading" && category !== null ? (
                  <span className="text-base font-semibold">{t("countChecking")}</span>
                ) : schemes === "failed" && category !== null ? null : linked ? (
                  <>
                    <span className="rounded-full bg-accent px-4 py-1 text-base font-bold text-on-accent">
                      {t(count === 1 ? "countOne" : "countMany", { count })}
                    </span>
                    <ArrowRight aria-hidden size={24} />
                  </>
                ) : (
                  <span className="rounded-full border-2 border-current px-4 py-0.5 text-base font-bold">{t("comingSoon")}</span>
                )}
              </span>
            </>
          );

          const shape = `flex h-full flex-col gap-4 rounded-3xl p-6 shadow-card ${TONE[tone]}`;
          return (
            <li key={key}>
              {linked ? (
                <Link href={`/schemes#group-${category}`} className={`${shape} transition duration-200 hover:-translate-y-1 hover:shadow-lift`}>
                  {body}
                </Link>
              ) : (
                <div className={shape}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
      {schemes === "failed" && <p role="status" className="text-lg text-muted">{t("countsFailed")}</p>}
    </>
  );
}
