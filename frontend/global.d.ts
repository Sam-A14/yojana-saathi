import type { en } from "./messages/en";

// Tells next-intl which message keys exist, so a typo in t("home.titel") fails type-check.
declare module "next-intl" {
  interface AppConfig {
    Locale: "en" | "hi";
    Messages: typeof en;
  }
}
