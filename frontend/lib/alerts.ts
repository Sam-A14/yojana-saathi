// "What's new for your family": which sentence an alert gets, and the words to put in it. The server
// sends facts only (who, which scheme, which age); the sentences are in messages/ (English, Hindi).

import type { AlertItem, AlertScheme } from "./types";

type Locale = "en" | "hi";

const schemeName = (scheme: AlertScheme, locale: Locale): string => (locale === "hi" && scheme.name_hi) || scheme.name_en;

export type AlertTextKey = "newScheme" | "ruleChange" | "ageThreshold";

/** The message key (under "alerts.text") and the words for its blanks. */
export function alertText(alert: AlertItem, locale: Locale): { key: AlertTextKey; values: Record<string, string | number> } {
  switch (alert.type) {
    case "new_scheme":
      return { key: "newScheme", values: { member: alert.payload.member, scheme: schemeName(alert.payload.scheme, locale) } };
    case "rule_change":
      return { key: "ruleChange", values: { scheme: schemeName(alert.payload.scheme, locale) } };
    case "age_threshold":
      return {
        key: "ageThreshold",
        values: {
          member: alert.payload.member,
          age: alert.payload.age,
          // No thousands separator in a year ("2027", not "2,027"): a string is never formatted.
          year: String(alert.payload.year),
          schemes: alert.payload.schemes.map((s) => schemeName(s, locale)).join(", "),
        },
      };
  }
}

/** Newest first is the server's order; this only counts what is still unread. */
export const unreadCount = (alerts: AlertItem[]): number => alerts.filter((a) => !a.read).length;
