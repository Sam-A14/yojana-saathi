"use client";

import { useTranslations } from "next-intl";
import { ButtonLink } from "@/components/ui";
import { useStoredFamily } from "@/lib/storage";

// A placeholder: the family dashboard replaces this page in the next pull request.
export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const { ready, family } = useStoredFamily();

  if (!ready) return <p>{tc("loading")}</p>;
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{family ? t("title") : t("none")}</h1>
      {family && <p>{t("body")}</p>}
      <ButtonLink href="/" variant="secondary">
        {t("toStart")}
      </ButtonLink>
    </div>
  );
}
