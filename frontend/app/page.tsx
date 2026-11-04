import { getTranslations } from "next-intl/server";
import { ButtonLink } from "@/components/ui";

export default async function Home() {
  const t = await getTranslations("home");
  return (
    <div className="flex flex-col gap-6 py-6">
      <h1 className="text-3xl font-bold leading-tight">{t("title")}</h1>
      <p className="text-lg">{t("intro")}</p>
      <div className="flex flex-col gap-3">
        <ButtonLink href="/setup/basics">{t("start")}</ButtonLink>
        <ButtonLink href="/resume" variant="secondary">
          {t("resume")}
        </ButtonLink>
      </div>
      <p className="text-base text-zinc-600 dark:text-zinc-400">{t("free")}</p>
    </div>
  );
}
