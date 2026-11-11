"use client";

import { Hourglass } from "lucide-react";
import { useTranslations } from "next-intl";
import { useServerWaking } from "@/lib/slow-requests";

/** Shown while a request has been waiting for more than 3 seconds: the free host sleeps when idle
 * and takes up to a minute to wake. The live region is always there (empty), so a screen reader
 * announces the message when it appears. */
export function WakingBanner() {
  const t = useTranslations("common");
  const waking = useServerWaking();
  return (
    <div role="status" aria-live="polite" className="sticky top-0 z-30 print:hidden">
      {waking && (
        <p className="flex items-center justify-center gap-3 bg-accent px-4 py-3 text-center text-lg font-bold text-on-accent shadow-lift">
          <Hourglass size={24} className="shrink-0" />
          {t("waking")}
        </p>
      )}
    </div>
  );
}
