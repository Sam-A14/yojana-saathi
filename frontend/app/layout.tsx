import type { Metadata } from "next";
import { Noto_Sans_Devanagari, Plus_Jakarta_Sans } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { AppHeader } from "@/components/AppHeader";
import { Footer } from "@/components/Footer";
import { TEXT_SIZE_KEY } from "@/lib/text-size";
import "./globals.css";

// One variable file each (all weights in a single download). Headings use 700 and 800.
const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  display: "swap",
});

// Plus Jakarta Sans has no Devanagari letters, so Hindi text needs its own font to look the same
// everywhere. Not preloaded: the browser downloads it only when a page actually shows Hindi
// letters, so English readers never pay for it.
const devanagari = Noto_Sans_Devanagari({
  variable: "--font-devanagari",
  subsets: ["devanagari"],
  display: "swap",
  preload: false,
});

// Allowed to block: the language comes from a cookie, which only exists at request time, so the
// pages cannot be built ahead of time. See docs/decisions/013-language-cookie.md.
export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("meta");
  return { title: t("title"), description: t("description") };
}

// Runs before the first paint, so a person who chose "A+" never sees the page jump in size.
// localStorage can be blocked (private mode), hence the try/catch.
const applyTextSize = `try{if(localStorage.getItem("${TEXT_SIZE_KEY}")==="large")document.documentElement.dataset.textSize="large"}catch(e){}`;

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const locale = await getLocale();
  return (
    // suppressHydrationWarning: the script above sets data-text-size on <html> before React runs.
    <html
      lang={locale}
      className={`${jakarta.variable} ${devanagari.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: applyTextSize }} />
      </head>
      <body className="flex min-h-full flex-col">
        <NextIntlClientProvider>
          <AppHeader />
          <main className="flex-1">{children}</main>
          <Footer />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
