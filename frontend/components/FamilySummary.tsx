"use client";

import { useTranslations } from "next-intl";
import { Celebration } from "./Celebration";
import { SECTION_ICONS, StatusIcon } from "./icons";
import type { ResultKind } from "./StatusBadge";

type Counts = { fit: number; close: number; unsure: number };

// The three groups with their result colours. Each is a number, an icon AND a word.
const TILES: { key: keyof Counts; kind: ResultKind; colours: string }[] = [
  { key: "fit", kind: "eligible", colours: "bg-ok-bg text-ok-fg" },
  { key: "close", kind: "near_miss", colours: "bg-close-bg text-close-fg" },
  { key: "unsure", kind: "unknown", colours: "bg-ask-bg text-ask-fg" },
];

/** The warm card at the top of the dashboard and the example: one sentence for the whole family,
 * then the three numbers. When somebody may qualify, a small burst of paper plays once (CSS only). */
export function FamilySummary({ counts, checkedOn }: { counts: Counts; checkedOn?: string }) {
  const t = useTranslations("dashboard");
  const ts = useTranslations("status");
  const Party = SECTION_ICONS.celebrate;
  return (
    <section
      aria-label={t("title")}
      className="flex flex-col gap-5 rounded-3xl border border-line-soft bg-gradient-to-br from-primary-soft to-soft p-5 shadow-card"
    >
      <div className="flex items-start gap-4">
        {counts.fit > 0 && (
          <span className="relative mt-1 shrink-0">
            <span aria-hidden className="pop flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-on-accent shadow-lift">
              <Party size={30} />
            </span>
            <Celebration />
          </span>
        )}
        <div className="flex flex-col gap-1">
          <p className="text-lg font-semibold">{t("summary", counts)}</p>
          {checkedOn && <p className="text-base text-muted">{t("checkedOn", { date: checkedOn })}</p>}
        </div>
      </div>
      <ul className="grid grid-cols-3 gap-3">
        {TILES.map(({ key, kind, colours }) => (
          <li key={key} className={`flex flex-col items-center gap-1 rounded-2xl px-2 py-3 text-center ${colours}`}>
            <StatusIcon kind={kind} size={22} />
            <span className="text-3xl font-extrabold leading-none">{counts[key]}</span>
            <span className="text-base font-bold leading-tight">{ts(kind)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
