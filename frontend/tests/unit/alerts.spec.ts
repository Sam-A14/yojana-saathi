import { expect, test } from "@playwright/test";
import { alertText, unreadCount } from "../../lib/alerts";
import type { AlertItem } from "../../lib/types";

// Which sentence an alert gets and the words in it. The server sends facts only.

const scheme = { slug: "ignoaps", name_en: "Old Age Pension", name_hi: "वृद्धावस्था पेंशन" };
const base = { id: 1, created_at: "2026-11-03T00:00:00Z", read: false };

test("a scheme that now fits names the person and the scheme, in the chosen language", () => {
  const alert: AlertItem = { ...base, type: "new_scheme", payload: { member: "Dadi", scheme } };
  expect(alertText(alert, "en")).toEqual({ key: "newScheme", values: { member: "Dadi", scheme: "Old Age Pension" } });
  expect(alertText(alert, "hi").values.scheme).toBe("वृद्धावस्था पेंशन");
});

test("a scheme with no Hindi name shows its English name in Hindi", () => {
  const alert: AlertItem = { ...base, type: "rule_change", payload: { scheme: { ...scheme, name_hi: null }, version_no: 2 } };
  expect(alertText(alert, "hi")).toEqual({ key: "ruleChange", values: { scheme: "Old Age Pension" } });
});

test("an age alert lists every scheme that starts at that age, and keeps the year plain", () => {
  const other = { slug: "x", name_en: "Other", name_hi: null };
  const alert: AlertItem = { ...base, type: "age_threshold", payload: { member: "Bua", age: 60, year: 2027, schemes: [scheme, other] } };
  const { key, values } = alertText(alert, "en");
  expect(key).toBe("ageThreshold");
  expect(values).toEqual({ member: "Bua", age: 60, year: "2027", schemes: "Old Age Pension, Other" });
});

test("only unread alerts are counted", () => {
  const read: AlertItem = { ...base, id: 2, read: true, type: "rule_change", payload: { scheme, version_no: 2 } };
  const unread: AlertItem = { ...base, id: 3, type: "rule_change", payload: { scheme, version_no: 3 } };
  expect(unreadCount([read, unread, unread])).toBe(2);
  expect(unreadCount([])).toBe(0);
});
