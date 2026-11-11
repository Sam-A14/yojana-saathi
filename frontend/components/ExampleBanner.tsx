"use client";

import { useTranslations } from "next-intl";
import { ButtonLink } from "./ui";

/** On every example page, so nobody mistakes it for their own results. */
export function ExampleBanner() {
  const t = useTranslations("example");
  return (
    <aside className="flex flex-col gap-4 rounded-2xl border-2 border-accent-ink bg-soft p-5">
      <p>
        <span className="inline-flex rounded-full bg-accent px-4 py-1.5 text-base font-extrabold text-on-accent">
          {t("label")}
        </span>
      </p>
      <p className="text-lg">{t("banner")}</p>
      <ButtonLink href="/setup/basics">{t("cta")}</ButtonLink>
    </aside>
  );
}
