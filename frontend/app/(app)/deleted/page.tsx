import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ButtonLink } from "@/components/ui";

// Its own page, not a message inside the dashboard: Next.js keeps hidden pages' state, so a
// "deleted" flag kept there would greet the next family on this phone with the wrong message.
export default async function DeletedPage() {
  const t = await getTranslations("privacy");
  const td = await getTranslations("dashboard");
  const tp = await getTranslations("privacyPage");
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t("deletedTitle")}</h1>
      <p>{t("deletedBody")}</p>
      <p className="text-base text-muted">{t("deletedNote")}</p>
      <Link href="/privacy" className="inline-flex min-h-12 items-center font-bold text-primary underline">
        {tp("link")}
      </Link>
      <ButtonLink href="/" variant="secondary">
        {td("toStart")}
      </ButtonLink>
    </div>
  );
}
