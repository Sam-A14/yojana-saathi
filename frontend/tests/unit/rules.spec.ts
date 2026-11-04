import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { createTranslator } from "use-intl";
import { en } from "../../messages/en";
import { hi } from "../../messages/hi";
import { describeRule, toTranslate } from "../../lib/rule-text";
import { neededAnswers, parseRule } from "../../lib/rules";
import type { Eligibility } from "../../lib/types";
import eligibility from "../fixtures/eligibility.json";

const DOCUMENTS: Record<string, string> = {
  bpl_card: "BPL (below poverty line) card",
  bank_account_aadhaar_linked: "Bank account linked to Aadhaar",
};

function words(locale: "en" | "hi") {
  const translator = createTranslator({ locale, messages: locale === "hi" ? hi : en });
  const env = {
    translate: toTranslate(translator),
    locale,
    documentName: (code: string) => DOCUMENTS[code] ?? code,
  };
  return (rule: unknown) => describeRule(rule, env);
}

// Every top-level rule of every hand-labelled scheme (the same files the backend seeds from).
function seedRules(): { scheme: string; rule: unknown }[] {
  const dir = path.resolve(__dirname, "../../../data/schemes_seed");
  return readdirSync(dir)
    .filter((name) => name.endsWith(".json"))
    .flatMap((name) => {
      const scheme = JSON.parse(readFileSync(path.join(dir, name), "utf8"));
      return (scheme.version.rules.all as unknown[]).map((rule) => ({ scheme: name, rule }));
    });
}

test.describe("every seeded scheme rule can be shown in words", () => {
  for (const locale of ["en", "hi"] as const) {
    test(`in ${locale}`, () => {
      const describe = words(locale);
      const rules = seedRules();
      expect(rules.length).toBeGreaterThan(10);
      for (const { scheme, rule } of rules) {
        expect(parseRule(rule), `${scheme}: ${JSON.stringify(rule)} was not understood`).not.toBeNull();
        const text = describe(rule);
        expect(text, `${scheme}: ${JSON.stringify(rule)}`).not.toBe("");
        expect(text, `${scheme}: raw key or placeholder leaked`).not.toMatch(/rules\.|options\.|[{}]/);
        expect(text, `${scheme}: fell back to the "cannot show" sentence`).not.toBe(
          locale === "hi" ? hi.rules.unknownFact : en.rules.unknownFact,
        );
      }
    });
  }
});

test.describe("the wording of the rules a family sees", () => {
  const english = words("en");

  test("exclusions read as 'no one in the family'", () => {
    const rule = { not: { any_member: { field: "paid_income_tax_last_year", op: "is_true" } } };
    expect(english(rule)).toBe("No one in the family: Paid income tax last year");
  });

  test("a requirement on someone reads as 'at least one person'", () => {
    const rule = { any_member: { field: "owns_cultivable_land", op: "is_true" } };
    expect(english(rule)).toBe("At least one person in the family: Owns farmland");
  });

  test("numbers, words, papers and money", () => {
    expect(english({ field: "age", op: "gte", value: 40 })).toBe("Age: 40 or more");
    expect(english({ field: "marital_status", op: "eq", value: "widow" })).toBe("Marital status: Widowed");
    expect(english({ field: "has_bpl_card", op: "is_true" })).toBe("Has BPL (below poverty line) card");
    expect(english({ field: "income_band_max", op: "lte", value: 150000 })).toBe(
      "Family income in a year: ₹1,50,000 or less",
    );
  });

  test("a group of choices and a combined condition", () => {
    const either = {
      any: [
        { field: "category", op: "in", value: ["SC", "OBC"] },
        { field: "area_type", op: "eq", value: "rural" },
      ],
    };
    expect(english(either)).toBe(
      "At least one of these: Social category: SC (Scheduled Caste) or OBC (Other Backward Classes); Where the family lives: Village (rural)",
    );
    const pension = {
      not: {
        any_member: {
          all: [
            { field: "pension_band", op: "eq", value: "10k_plus" },
            { field: "govt_employee", op: "neq", value: "group_d" },
          ],
        },
      },
    };
    expect(english(pension)).toBe(
      "No one in the family: Government pension: ₹10,000 a month or more and Government job: not Lowest-level post (Group D)",
    );
  });

  test("Hindi uses the Hindi words", () => {
    const rule = { not: { any_member: { field: "paid_income_tax_last_year", op: "is_true" } } };
    expect(words("hi")(rule)).toBe("परिवार में कोई भी नहीं: पिछले साल आयकर दिया");
  });

  test("anything not understood says so plainly instead of showing JSON", () => {
    for (const locale of ["en", "hi"] as const) {
      const text = words(locale)({ field: "favourite_colour", op: "eq", value: "blue" });
      expect(text).toBe(locale === "hi" ? hi.rules.unknownFact : en.rules.unknownFact);
    }
    expect(words("en")({ surprise: true })).toBe(en.rules.unknownFact);
    expect(words("en")("not even an object")).toBe(en.rules.unknownFact);
    expect(parseRule({ field: "age", op: "sideways", value: 1 })).toBeNull();
    expect(parseRule({ all: [] })).toBeNull();
  });
});

test.describe("what a family can answer to settle an unknown result", () => {
  const data = eligibility as unknown as Eligibility;
  const result = (member: string, slug: string) =>
    data.members.find((m) => m.nickname === member)!.schemes.find((s) => s.scheme.slug === slug)!;

  test("a missing paper is a question that can be answered on the documents screen", () => {
    const needs = neededAnswers(result("Kamla", "example-scholarship"));
    expect(needs.needs).toEqual([
      { field: "has_bank_account_aadhaar_linked", familyWide: false, link: "/setup/documents" },
    ]);
    expect(needs.reasons).toEqual([]);
  });

  test("exact age and exact income are explained, not asked", () => {
    const age = neededAnswers(result("Asha", "ignwps"));
    expect(age).toEqual({ needs: [], reasons: ["depends_on_exact_age"] });
    const income = neededAnswers(result("Kamla", "example-income-limit"));
    expect(income).toEqual({ needs: [], reasons: ["depends_on_exact_income"] });
  });

  test("a family-wide rule asks about everyone and points to the right screen", () => {
    const rule = { not: { any_member: { field: "paid_income_tax_last_year", op: "is_true" } } };
    const needs = neededAnswers({
      reasons: [],
      unknown_rules: [
        { rule, fields: ["paid_income_tax_last_year"], matched_members: [], fixable: false, reasons: [] },
      ],
    });
    expect(needs.needs).toEqual([
      { field: "paid_income_tax_last_year", familyWide: true, link: "/setup/exclusions" },
    ]);
  });

  test("the same fact is never asked twice, and home facts have no screen yet", () => {
    const rule = { field: "income_band_max", op: "lte", value: 1 };
    const unknown = { rule, fields: ["income_band_max"], matched_members: [], fixable: false, reasons: [] };
    const needs = neededAnswers({ reasons: [], unknown_rules: [unknown, unknown] });
    expect(needs.needs).toEqual([{ field: "income_band_max", familyWide: false, link: null }]);
  });
});
