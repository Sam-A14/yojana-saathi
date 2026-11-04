import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { LanguageToggle } from "./LanguageToggle";

export async function AppHeader() {
  const t = await getTranslations("common");
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800 print:hidden">
      <div className="mx-auto flex w-full max-w-xl items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-lg font-bold">
          {t("appName")}
        </Link>
        <LanguageToggle />
      </div>
    </header>
  );
}
