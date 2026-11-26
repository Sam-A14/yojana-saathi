import { getTranslations } from "next-intl/server";
import { SchemesList } from "@/components/SchemesList";
import { ButtonLink } from "@/components/ui";

// Public: anyone can see which schemes we check, before they give an email. Nothing about a family.
export default async function SchemesPage() {
  const t = await getTranslations("schemesPage");
  return (
    <div className="flex flex-col gap-6">
      <h1 className="page-title">{t("title")}</h1>
      <p className="text-lg">{t("intro")}</p>
      <ButtonLink href="/setup/basics">{t("cta")}</ButtonLink>
      <SchemesList />
    </div>
  );
}
