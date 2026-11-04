import { type Condition, parseRule } from "./rules";
import { STATES } from "./states";

// Turns a parsed rule into plain words ("No one in the family: Paid income tax last year").
// Pure: the words come from messages/ through `translate`, so the same code serves both languages
// and can be tested without React. If anything is not understood, the answer is a plain "we cannot
// show this in words yet" sentence, never raw JSON.

export type Translate = (key: string, values?: Record<string, string | number>) => string;

export type RuleTextEnv = {
  translate: Translate;
  locale: "en" | "hi";
  documentName: (code: string) => string;
};

/** Adapt a next-intl translator (whose keys are checked one by one) to one that takes any key as
 * text. Keys built at run time, such as `rules.field.${name}`, cannot be checked ahead of time, so
 * this one adapter does the check with has(): a key we have no message for comes back as the key
 * itself. The unit tests run every real rule through it in both languages. */
export function toTranslate(translator: unknown): Translate {
  const t = translator as {
    (key: string, values?: Record<string, string | number>): string;
    has(key: string): boolean;
  };
  return (key, values) => (t.has(key) ? t(key, values) : key);
}

// Facts whose answers are words in a fixed list, and where those words live in messages/.
const VALUE_WORDS: Record<string, string> = {
  gender: "options.gender",
  marital_status: "options.marital",
  occupation: "options.occupation",
  education: "options.education",
  category: "options.category",
  area_type: "options.area",
  govt_employee: "rules.value.govt",
  pension_band: "rules.value.pension",
};

function formatValue(field: string, value: unknown, env: RuleTextEnv): string {
  if (typeof value === "boolean") return env.translate(value ? "rules.yes" : "rules.no");
  if (typeof value === "number") {
    // Income limits are rupees; Indian grouping (1,50,000) is how people read them.
    return field === "income_band_max"
      ? `₹${new Intl.NumberFormat("en-IN").format(value)}`
      : String(value);
  }
  if (typeof value !== "string") return String(value);
  if (field === "state") {
    const state = STATES.find((s) => s.code === value);
    return state ? state[env.locale] : value;
  }
  const words = VALUE_WORDS[field];
  return words ? env.translate(`${words}.${value}`) : value;
}

function conditionText(field: string, op: string, value: unknown, env: RuleTextEnv): string | null {
  const { translate } = env;
  if (op === "between" && Array.isArray(value) && value.length === 2) {
    return translate("rules.op.between", {
      from: formatValue(field, value[0], env),
      to: formatValue(field, value[1], env),
    });
  }
  if ((op === "in" || op === "not_in") && Array.isArray(value)) {
    const list = new Intl.ListFormat(env.locale, { type: "disjunction" }).format(
      value.map((v) => formatValue(field, v, env)),
    );
    return translate(`rules.op.${op}`, { value: list });
  }
  if (["eq", "neq", "gte", "lte"].includes(op) && value !== undefined && value !== null) {
    return translate(`rules.op.${op}`, { value: formatValue(field, value, env) });
  }
  return null;
}

function factText(field: string, op: string, value: unknown, env: RuleTextEnv): string {
  const { translate } = env;
  const label = field.startsWith("has_")
    ? translate("rules.hasDocument", { document: env.documentName(field.slice(4)) })
    : translate(`rules.field.${field}`);
  // translate() returns the key itself for a missing message: that means "a field we have no words for".
  if (label.startsWith("rules.field.")) return translate("rules.unknownFact");
  if (op === "is_true") return label; // "Owns farmland" already says it
  const condition = conditionText(field, op, value, env);
  return condition ? `${label}: ${condition}` : translate("rules.unknownFact");
}

export function describeCondition(condition: Condition, env: RuleTextEnv): string {
  const { translate } = env;
  const text = (c: Condition) => describeCondition(c, env);
  switch (condition.type) {
    case "fact":
      return factText(condition.field, condition.op, condition.value, env);
    case "all":
      return condition.items
        .map(text)
        .reduce((first, second) => translate("rules.and", { first, second }));
    case "any":
      return translate("rules.anyOf", { items: condition.items.map(text).join("; ") });
    case "any_member":
      return translate("rules.someone", { text: text(condition.item) });
    case "not":
      // "No one in the family ..." is how every exclusion is written.
      return condition.item.type === "any_member"
        ? translate("rules.nobody", { text: text(condition.item.item) })
        : translate("rules.not", { text: text(condition.item) });
  }
}

/** One rule as the API sends it, in words. */
export function describeRule(raw: unknown, env: RuleTextEnv): string {
  const condition = parseRule(raw);
  return condition ? describeCondition(condition, env) : env.translate("rules.unknownFact");
}
