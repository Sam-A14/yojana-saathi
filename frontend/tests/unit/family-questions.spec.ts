import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { createTranslator } from "use-intl";
import { en } from "../../messages/en";
import { hi } from "../../messages/hi";
import { questionText } from "../../lib/question-text";
import { toTranslate } from "../../lib/rule-text";
import { neededAnswers } from "../../lib/rules";

// "No one in the family pays income tax" is unknown until the family says if anyone does. The
// question must be "Did ANYONE in your family pay income tax last year?". It once read "Did
// EVERYONE...", which asks for something else. One test per pattern of rule, in both languages.

const DOCUMENTS: Record<string, string> = { ration_card: "Ration card" };

function questions(locale: "en" | "hi", rule: Record<string, unknown>, memberName = "Asha"): string[] {
  const translate = toTranslate(createTranslator({ locale, messages: locale === "hi" ? hi : en }));
  const everyone = locale === "hi" ? hi.needs.everyone : en.needs.everyone;
  const result = {
    unknown_rules: [{ rule, fields: factsIn(rule), matched_members: [], fixable: false, reasons: [] }],
    reasons: [],
  };
  return neededAnswers(result as never).needs.map((need) =>
    questionText(translate, need, {
      memberName,
      everyone,
      documentName: (code) => DOCUMENTS[code] ?? code,
    }),
  );
}

function factsIn(node: unknown): string[] {
  if (Array.isArray(node)) return node.flatMap(factsIn);
  if (node && typeof node === "object") {
    const object = node as Record<string, unknown>;
    if (typeof object.field === "string") return [object.field];
    return Object.values(object).flatMap(factsIn);
  }
  return [];
}

const yes = (field: string) => ({ field, op: "is_true" });

test.describe("the question for a rule about the whole family", () => {
  test("no member pays income tax (PMAY-Gramin): anyone, not everyone", () => {
    const rule = { not: { any_member: yes("paid_income_tax_last_year") } };

    expect(questions("en", rule)).toEqual(["Did anyone in your family pay income tax last year?"]);
    expect(questions("hi", rule)).toEqual(["क्या आपके परिवार में किसी ने पिछले साल आयकर दिया?"]);
  });

  test("at least one member owns farmland (PM-KISAN): anyone", () => {
    const rule = { any_member: yes("owns_cultivable_land") };

    expect(questions("en", rule)).toEqual(["Does anyone in your family own farmland?"]);
  });

  test("no member is a government employee or pensioner (an exclusion with a condition inside)", () => {
    const rule = {
      not: {
        any_member: {
          all: [
            { field: "pension_band", op: "eq", value: "10k_plus" },
            { field: "govt_employee", op: "neq", value: "group_d" },
          ],
        },
      },
    };

    expect(questions("en", rule)).toEqual([
      "Does anyone in your family get a government pension?",
      "Does anyone in your family work, or did they work, in a government job?",
    ]);
  });

  test("a member who is a student: anyone for the yes/no fact", () => {
    const rule = { any_member: { all: [yes("is_student"), { field: "age", op: "gte", value: 18 }] } };

    const asked = questions("en", rule);
    expect(asked).toContain("Is anyone in your family studying now?");
    expect(asked).toContain("What year was everyone in your family born?"); // a "what" fact: everyone
  });

  test("a 'what' fact about members is asked of everyone", () => {
    const rule = { any_member: { field: "occupation", op: "eq", value: "farmer" } };

    expect(questions("en", rule)).toEqual(["What is the main work of everyone in your family?"]);
  });

  test("a paper that some member must hold", () => {
    const rule = { any_member: yes("has_ration_card") };

    expect(questions("en", rule)).toEqual(["Does anyone in your family have this paper: Ration card?"]);
    expect(questions("hi", rule)).toEqual(["क्या आपके परिवार में किसी के पास यह कागज़ है: Ration card?"]);
  });

  test("a rule about one person still names the person", () => {
    const rule = yes("paid_income_tax_last_year");

    expect(questions("en", rule, "Asha")).toEqual(["Did Asha pay income tax last year?"]);
    expect(questions("hi", rule, "आशा")).toEqual(["क्या आशा ने पिछले साल आयकर दिया?"]);
  });

  test("a fact about the home is asked the same way whatever the rule around it", () => {
    const rule = { not: { any_member: yes("paid_income_tax_last_year") } };
    const mixed = { all: [{ field: "area_type", op: "eq", value: "rural" }, rule] };

    expect(questions("en", mixed)).toEqual([
      "Does your family live in a village or a town?",
      "Did anyone in your family pay income tax last year?",
    ]);
  });
});

test.describe("every fact has a whole-family sentence, in both languages", () => {
  // The facts the engine reads for a person (backend/app/rules/fields.py). A new one must get a
  // sentence here, or it would be asked as "everyone in your family", which fits only some facts.
  function engineMemberFields(): string[] {
    const source = readFileSync(path.resolve(__dirname, "../../../backend/app/rules/fields.py"), "utf8");
    const block = source.match(/MEMBER_FIELDS = frozenset\(\s*\{([^}]*)\}/);
    if (!block) throw new Error("MEMBER_FIELDS not found in backend/app/rules/fields.py");
    return [...block[1].matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);
  }

  // Yes/no facts: one "yes" from anyone settles them.
  const YES_NO = [
    "is_student",
    "disability",
    "owns_cultivable_land",
    "is_remarried",
    "paid_income_tax_last_year",
    "govt_employee",
    "pension_band",
    "is_registered_professional",
    "holds_constitutional_post",
    "document",
  ];

  for (const [locale, messages] of [["en", en], ["hi", hi]] as const) {
    test(`in ${locale}`, () => {
      const family = messages.familyQuestions as Record<string, string>;
      for (const field of [...engineMemberFields(), "document"]) {
        expect(family[field], `${field} has no sentence in familyQuestions`).toBeTruthy();
        expect(family[field], `${field}: a family sentence must not name one person`).not.toContain("{name}");
      }
      if (locale === "en") {
        for (const field of YES_NO) expect(family[field], field).toMatch(/\banyone\b/);
        for (const field of YES_NO) expect(family[field], field).not.toMatch(/\beveryone\b/);
      }
    });
  }
});
