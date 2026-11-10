"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { LanguageToggle } from "./LanguageToggle";
import { Logo } from "./Logo";
import { TextSizeToggle } from "./TextSizeToggle";

export function AppHeader() {
  const t = useTranslations("common");
  // The home page opens with a dark green hero; the header joins it so the first screen is one piece.
  const onDark = usePathname() === "/";
  return (
    <header
      className={`print:hidden ${
        onDark ? "on-dark bg-hero text-on-hero" : "border-b border-line-soft bg-surface"
      }`}
    >
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-3 px-4 py-3">
        <Link href="/" className="flex min-h-12 items-center gap-3 text-xl font-extrabold">
          <Logo />
          {t("appName")}
        </Link>
        <div className="flex items-center gap-2">
          <TextSizeToggle onDark={onDark} />
          <LanguageToggle onDark={onDark} />
        </div>
      </div>
    </header>
  );
}
