import type { ReasonCode, RuleResult, SchemeResult } from "./types";

// A scheme rule is JSON (docs/decisions/005, data/README.md). The API sends each top-level rule
// exactly as written, so the screen can show it. This file turns that JSON into a typed tree
// (parseRule) and works out which questions a family could answer to settle an "unknown".
// It decides nothing about eligibility: that is always the backend rules engine.

export type Condition =
  | { type: "fact"; field: string; op: Operator; value: unknown }
  | { type: "all" | "any"; items: Condition[] }
  | { type: "not"; item: Condition }
  | { type: "any_member"; item: Condition };

const OPERATORS = ["eq", "neq", "in", "not_in", "gte", "lte", "between", "is_true"] as const;
export type Operator = (typeof OPERATORS)[number];

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** Read one rule from the API. Returns null for any shape we do not know, never guesses. */
export function parseRule(raw: unknown): Condition | null {
  if (!isObject(raw)) return null;
  if (Array.isArray(raw.all) || Array.isArray(raw.any)) {
    const type = Array.isArray(raw.all) ? "all" : "any";
    const children = (raw[type] as unknown[]).map(parseRule);
    return children.length > 0 && children.every((c) => c !== null)
      ? { type, items: children as Condition[] }
      : null;
  }
  if ("not" in raw) {
    const item = parseRule(raw.not);
    return item && { type: "not", item };
  }
  if ("any_member" in raw) {
    const item = parseRule(raw.any_member);
    return item && { type: "any_member", item };
  }
  if (typeof raw.field === "string" && OPERATORS.includes(raw.op as Operator)) {
    return { type: "fact", field: raw.field, op: raw.op as Operator, value: raw.value };
  }
  return null;
}

/** True when the rule is about the whole household ("no one in the family..."), not one person. */
export function isFamilyWide(condition: Condition): boolean {
  switch (condition.type) {
    case "any_member":
      return true;
    case "not":
      return isFamilyWide(condition.item);
    case "all":
    case "any":
      return condition.items.some(isFamilyWide);
    case "fact":
      return false;
  }
}

// --- what a family could answer to settle an "unknown" ------------------------------------------

// Where an answer can be changed: the setup screens for people and papers, and the household
// details screen for facts about the home.
const EXCLUSION_FIELDS = [
  "paid_income_tax_last_year",
  "govt_employee",
  "pension_band",
  "is_registered_professional",
  "holds_constitutional_post",
];
const HOME_FIELDS = ["state", "district", "area_type", "income_band_max", "category"];

export type Need = {
  field: string; // "age", "gender", "has_bpl_card", ...
  familyWide: boolean; // ask about every person, not just this one
  link: string | null; // the screen where it can be answered
};

function setupScreenFor(field: string): string | null {
  if (field.startsWith("has_")) return "/setup/documents";
  if (EXCLUSION_FIELDS.includes(field)) return "/setup/exclusions";
  if (HOME_FIELDS.includes(field)) return "/household/edit";
  return "/setup/members";
}

export type NeededAnswers = {
  needs: Need[];
  // Unknown only because we hold a birth year or an income range, not the exact value. No answer
  // the family can give settles these, so the screen explains and points to the official page.
  reasons: ReasonCode[];
};

/** The questions behind an "unknown" result, one per fact, without repeats. */
export function neededAnswers(result: Pick<SchemeResult, "unknown_rules" | "reasons">): NeededAnswers {
  const needs = new Map<string, Need>();
  const reasons = new Set<ReasonCode>(result.reasons);
  for (const rule of result.unknown_rules) {
    for (const reason of rule.reasons) reasons.add(reason);
    const familyWide = isFamilyWide(parseRule(rule.rule) ?? { type: "all", items: [] });
    for (const field of factsToAsk(rule)) {
      const existing = needs.get(field);
      needs.set(field, {
        field,
        familyWide: familyWide || (existing?.familyWide ?? false),
        link: setupScreenFor(field),
      });
    }
  }
  return { needs: [...needs.values()], reasons: [...reasons] };
}

// A rule that is unknown because of an exact age or income range names a reason; the question
// "what is the exact age?" would have no answer we can store, so that field is not asked about.
function factsToAsk(rule: RuleResult): string[] {
  return rule.fields.filter((field) => {
    if (field === "age") return !rule.reasons.includes("depends_on_exact_age");
    if (field === "income_band_max") return !rule.reasons.includes("depends_on_exact_income");
    return true;
  });
}
