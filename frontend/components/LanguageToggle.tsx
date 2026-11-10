"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { LOCALE_COOKIE } from "@/i18n/constants";

// A plain cookie that lasts a year. It holds no personal data, so it needs no consent notice.
function rememberLanguage(language: "en" | "hi") {
  document.cookie = `${LOCALE_COOKIE}=${language}; path=/; max-age=31536000; samesite=lax`;
}

export function LanguageToggle({ onDark = false }: { onDark?: boolean }) {
  const locale = useLocale();
  const t = useTranslations("language");
  const router = useRouter();

  function choose(next: "en" | "hi") {
    rememberLanguage(next);
    router.refresh(); // render the page again in the new language
  }

  const look = onDark
    ? "aria-pressed:bg-on-hero aria-pressed:text-hero"
    : "aria-pressed:bg-primary aria-pressed:text-on-primary";
  return (
    <div
      role="group"
      aria-label={t("label")}
      className={`flex overflow-hidden rounded-xl border ${onDark ? "border-on-hero/60" : "border-line"}`}
    >
      {(["en", "hi"] as const).map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={locale === code}
          onClick={() => choose(code)}
          className={`min-h-12 px-3 text-base font-semibold transition-colors ${look}`}
        >
          {t(code)}
        </button>
      ))}
    </div>
  );
}
