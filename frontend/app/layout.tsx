import type { Metadata } from "next";
import { Geist, Noto_Sans_Devanagari } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { Footer } from "@/components/Footer";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Geist has no Devanagari letters, so Hindi text needs its own font to look the same everywhere.
const devanagari = Noto_Sans_Devanagari({
  variable: "--font-devanagari",
  subsets: ["devanagari"],
});

// Allowed to block: the language comes from a cookie, which only exists at request time, so the
// pages cannot be built ahead of time. See docs/decisions/013-language-cookie.md.
export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("meta");
  return { title: t("title"), description: t("description") };
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const locale = await getLocale();
  return (
    <html lang={locale} className={`${geistSans.variable} ${devanagari.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <NextIntlClientProvider>
          <AppHeader />
          <main className="mx-auto w-full max-w-xl flex-1 px-4 py-6">{children}</main>
          <Footer />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
