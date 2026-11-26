"use client";

import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";
import { THEME_KEY, THEMES, type Theme, toTheme } from "@/lib/theme";

// Like the A / A+ toggle: the choice lives on <html> (data-theme), because that is what the CSS
// reads. React watches it through useSyncExternalStore, so the buttons always match the page.
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => void listeners.delete(listener);
};
const currentTheme = (): Theme => toTheme(document.documentElement.dataset.theme);

function applyTheme(next: Theme) {
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    // Private mode or blocked storage: the theme still changes now, it just is not remembered.
  }
  listeners.forEach((listener) => listener());
}

const ICONS: Record<Theme, LucideIcon> = { light: Sun, dark: Moon, device: Monitor };

/** "Light / Dark / Match device". Every choice is an icon AND a word. Light is the default, so the
 * page never turns dark just because the phone is set to dark. */
export function ThemeToggle({ onDark = false }: { onDark?: boolean }) {
  const t = useTranslations("theme");
  // app/layout.tsx runs a tiny script before first paint that applies the saved choice.
  const current = useSyncExternalStore(subscribe, currentTheme, () => "light" as Theme);

  const border = onDark ? "border-on-hero/60" : "border-line";
  const pressed = onDark
    ? "aria-pressed:bg-on-hero aria-pressed:text-hero"
    : "aria-pressed:bg-primary aria-pressed:text-on-primary";
  return (
    <div role="group" aria-label={t("label")} className={`grid grid-cols-3 overflow-hidden rounded-xl border ${border}`}>
      {THEMES.map((choice) => {
        const Icon = ICONS[choice];
        return (
          <button
            key={choice}
            type="button"
            aria-pressed={current === choice}
            onClick={() => applyTheme(choice)}
            className={`flex min-h-12 items-center justify-center gap-2 px-3 text-center text-base font-semibold leading-tight transition-colors ${pressed}`}
          >
            <Icon aria-hidden size={20} className="shrink-0" />
            {t(choice)}
          </button>
        );
      })}
    </div>
  );
}
