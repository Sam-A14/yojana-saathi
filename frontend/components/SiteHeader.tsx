"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { clearSession, useSession } from "@/lib/session";
import { buttonClass } from "./button-styles";
import { LanguageToggle } from "./LanguageToggle";
import { Logo } from "./Logo";
import { TextSizeToggle } from "./TextSizeToggle";
import { ThemeToggle } from "./ThemeToggle";

// Two rows, like a public-service portal. The top strip always holds the two controls older readers
// need most (A / A+ and language) so they are never hidden behind a menu; the theme choice joins
// them from tablet width up. The main row holds the name, the tagline, the pages and Sign in (or "My family" and "Sign out" once signed in).
// Below the "xl" width the pages and Sign in move into a Menu (a button with a word, not just an icon).
const LINKS = [
  { key: "home", href: "/" },
  { key: "schemes", href: "/schemes" },
  { key: "howItWorks", href: "/#how" },
  { key: "faq", href: "/#faq" },
  { key: "about", href: "/#about" },
] as const;

export function SiteHeader() {
  const t = useTranslations("nav");
  const tc = useTranslations("common");
  const pathname = usePathname();
  const router = useRouter();
  const { ready, session } = useSession();
  const [open, setOpen] = useState(false);

  // Unlike the dashboard's "Sign out" (which explains first), this one acts at once: it is one tap
  // from every page, and signing in again with the same email brings everything back.
  async function signOut() {
    setOpen(false);
    // Best effort: if the server cannot be reached, this phone still forgets the session.
    if (session) await api.signOut(session.token).catch(() => undefined);
    clearSession();
    router.push("/");
  }

  // Escape closes the menu, as people expect.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const linkClass = (href: string) =>
    `inline-flex min-h-12 items-center rounded-xl px-3 text-lg font-semibold hover:bg-primary-soft ${
      pathname === href ? "text-primary underline decoration-accent decoration-4 underline-offset-8" : "text-ink"
    }`;

  return (
    <header className="print:hidden border-b border-line-soft bg-surface">
      <div className="border-b border-line-soft bg-soft">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-end gap-2 px-5 py-1 sm:px-4 sm:py-2">
          <TextSizeToggle />
          <LanguageToggle />
          <div className="hidden md:block">
            <ThemeToggle />
          </div>
        </div>
      </div>

      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-2 px-5 py-1.5 sm:gap-4 sm:px-4 sm:py-3">
        <Link href="/" className="flex min-h-[2.667rem] items-center gap-2 sm:min-h-12 sm:gap-3" onClick={() => setOpen(false)}>
          <Logo />
          <span className="flex flex-col">
            <span className="text-lg font-extrabold leading-tight sm:text-xl">{tc("appName")}</span>
            <span className="hidden max-w-[17rem] text-base leading-snug text-muted sm:block">{tc("tagline")}</span>
          </span>
        </Link>

        <nav aria-label={t("label")} className="hidden items-center gap-1 lg:flex">
          {LINKS.map((link) => (
            <Link key={link.key} href={link.href} className={linkClass(link.href)} aria-current={pathname === link.href ? "page" : undefined}>
              {t(link.key)}
            </Link>
          ))}
        </nav>

        {/* Before the browser's storage has been read we do not know who is here. The invisible
            "Sign in" keeps the row the same width, so nothing jumps and nobody sees a wrong button. */}
        {!ready ? (
          <span aria-hidden className={buttonClass("primary", "min-h-12! px-5! invisible max-lg:hidden")}>
            {t("signIn")}
          </span>
        ) : session ? (
          <div className="flex items-center gap-2 max-lg:hidden">
            <Link href="/dashboard" className={buttonClass("primary", "min-h-12! px-5!")}>
              {t("myFamily")}
            </Link>
            <button type="button" onClick={signOut} className={buttonClass("secondary", "min-h-12! px-5!")}>
              {t("signOut")}
            </button>
          </div>
        ) : (
          <Link href="/signin" className={buttonClass("primary", "min-h-12! px-5! max-lg:hidden")}>
            {t("signIn")}
          </Link>
        )}

        <button
          type="button"
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((value) => !value)}
          className="inline-flex min-h-[2.667rem] items-center gap-2 rounded-xl border-2 border-primary px-3 sm:min-h-12 sm:px-4 text-lg font-bold text-primary hover:bg-primary-soft lg:hidden"
        >
          {open ? <X aria-hidden size={22} /> : <Menu aria-hidden size={22} />}
          {open ? t("closeMenu") : t("menu")}
        </button>
      </div>

      {open && (
        <nav id="mobile-menu" aria-label={t("label")} className="border-t border-line-soft bg-surface lg:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-4 py-4">
            {LINKS.map((link) => (
              <Link
                key={link.key}
                href={link.href}
                onClick={() => setOpen(false)}
                aria-current={pathname === link.href ? "page" : undefined}
                className={`${linkClass(link.href)} w-full`}
              >
                {t(link.key)}
              </Link>
            ))}
            <div className="mt-2 md:hidden">
              <ThemeToggle />
            </div>
            {session ? (
              <>
                <Link href="/dashboard" onClick={() => setOpen(false)} className={buttonClass("primary", "mt-3 w-full")}>
                  {t("myFamily")}
                </Link>
                <button type="button" onClick={signOut} className={buttonClass("secondary", "w-full")}>
                  {t("signOut")}
                </button>
              </>
            ) : (
              <Link href="/signin" onClick={() => setOpen(false)} className={buttonClass("primary", "mt-3 w-full")}>
                {t("signIn")}
              </Link>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
