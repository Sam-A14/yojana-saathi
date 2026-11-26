import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { GITHUB_URL } from "@/lib/links";

// The Pexels page of the hero photo (Pexels licence: credit is kind, not required; we give it).
const PHOTO_URL = "https://www.pexels.com/photo/outdoor-family-portrait-with-generations-in-focus-34572616/";

/** On every page. Says plainly who we are NOT: no government emblem, no official logo, nothing that
 * suggests an official affiliation. */
export async function Footer() {
  const t = await getTranslations("footer");
  const tp = await getTranslations("privacyPage");
  const link = "inline-flex min-h-12 items-center gap-2 font-bold underline underline-offset-4";
  return (
    <footer className="on-dark bg-hero text-on-hero print:hidden">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-3 px-4 py-10">
        <p className="text-lg font-bold">{t("independent")}</p>
        <p className="text-base text-on-hero-muted">
          {t("disclaimer")} {t("noAadhaar")}
        </p>
        <div className="flex flex-wrap gap-x-8 gap-y-1">
          <Link href="/privacy" className={link}>
            {tp("link")}
          </Link>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className={link}>
            {t("github")}
            <ExternalLink aria-hidden size={18} />
          </a>
        </div>
        <p className="text-base text-on-hero-muted">
          <a href={PHOTO_URL} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-12 items-center underline underline-offset-4">
            {t("photoCredit")}
          </a>
        </p>
      </div>
    </footer>
  );
}
