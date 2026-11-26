import Link from "next/link";
import { getTranslations } from "next-intl/server";

export async function Footer() {
  const t = await getTranslations("footer");
  const tp = await getTranslations("privacyPage");
  return (
    <footer className="border-t border-line-soft bg-soft print:hidden">
      <div className="mx-auto flex w-full max-w-5xl flex-col items-start gap-1 px-4 py-6 text-base text-muted">
        <p>
          {t("disclaimer")} {t("noAadhaar")}
        </p>
        <Link href="/privacy" className="inline-flex min-h-12 items-center font-bold text-primary underline">
          {tp("link")}
        </Link>
      </div>
    </footer>
  );
}
