"use client";

import { useTranslations } from "next-intl";
import { StatusIcon } from "./icons";

export type ResultKind = "eligible" | "near_miss" | "unknown" | "excluded";

// An icon and a word as well as a colour, so the meaning never depends on seeing colours.
const COLOURS: Record<ResultKind, string> = {
  eligible: "bg-ok-bg text-ok-fg",
  near_miss: "bg-close-bg text-close-fg",
  unknown: "bg-ask-bg text-ask-fg",
  excluded: "bg-block-bg text-block-fg",
};

export function StatusBadge({ kind }: { kind: ResultKind }) {
  const t = useTranslations("status");
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-base font-bold ${COLOURS[kind]}`}
    >
      <StatusIcon kind={kind} size={20} />
      {t(kind)}
    </span>
  );
}
