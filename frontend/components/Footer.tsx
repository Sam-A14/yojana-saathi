import { getTranslations } from "next-intl/server";

export async function Footer() {
  const t = await getTranslations("footer");
  return (
    <footer className="border-t border-line-soft bg-soft print:hidden">
      <p className="mx-auto w-full max-w-5xl px-4 py-6 text-base text-muted">
        {t("disclaimer")} {t("noAadhaar")}
      </p>
    </footer>
  );
}
