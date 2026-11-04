"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { LOCALE_COOKIE } from "@/i18n/constants";

// A plain cookie that lasts a year. It holds no personal data, so it needs no consent notice.
function rememberLanguage(language: "en" | "hi") {
  document.cookie = `${LOCALE_COOKIE}=${language}; path=/; max-age=31536000; samesite=lax`;
}

export function LanguageToggle() {
  const locale = useLocale();
  const t = useTranslations("language");
  const router = useRouter();

  function choose(next: "en" | "hi") {
    rememberLanguage(next);
    router.refresh(); // render the page again in the new language
  }

  return (
    <div role="group" aria-label={t("label")} className="flex overflow-hidden rounded-lg border border-zinc-400 dark:border-zinc-600">
      {(["en", "hi"] as const).map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={locale === code}
          onClick={() => choose(code)}
          className="min-h-10 px-3 text-base aria-pressed:bg-emerald-700 aria-pressed:font-semibold aria-pressed:text-white"
        >
          {t(code)}
        </button>
      ))}
    </div>
  );
}
