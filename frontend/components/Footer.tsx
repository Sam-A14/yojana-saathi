import { getTranslations } from "next-intl/server";

export async function Footer() {
  const t = await getTranslations("footer");
  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800 print:hidden">
      <p className="mx-auto w-full max-w-xl px-4 py-4 text-sm text-zinc-600 dark:text-zinc-400">
        {t("disclaimer")} {t("noAadhaar")}
      </p>
    </footer>
  );
}
