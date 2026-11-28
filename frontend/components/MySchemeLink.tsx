"use client";

import { ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";
import { mySchemeUrl } from "@/lib/myscheme";

/** "See more schemes on myScheme": opens myScheme's search in a new tab. We do not check those
 * schemes, and the label says so. */
export function MySchemeLink({ words = [] }: { words?: string[] }) {
  const t = useTranslations("myScheme");
  return (
    <a
      href={mySchemeUrl(words)}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex min-h-12 items-center gap-2 self-start py-3 text-lg font-semibold underline"
    >
      {t("link")}
      <ExternalLink aria-hidden size={20} className="shrink-0" />
      <span className="sr-only">{t("newTab")}</span>
    </a>
  );
}
