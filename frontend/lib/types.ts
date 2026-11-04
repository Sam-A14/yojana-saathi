// What the API sends and accepts (backend/app/api/schemas.py). Written by hand because the API is
// small; if it grows, generate these from /openapi.json instead.

export type Family = { id: string; token: string };

export type HouseholdFields = {
  state: string | null;
  district: string | null;
  area_type: string | null;
  income_band: string | null;
  category: string | null;
};
export type Household = HouseholdFields & { id: string };
export type HouseholdCreated = Household & { access_token: string };

export type MemberFields = {
  birth_year: number | null;
  gender: string | null;
  marital_status: string | null;
  occupation: string | null;
  education: string | null;
  is_student: boolean | null;
  disability: boolean | null;
  owns_cultivable_land: boolean | null;
  is_remarried: boolean | null;
  // The PM-KISAN exclusion questions.
  paid_income_tax_last_year: boolean | null;
  govt_employee: string | null;
  pension_band: string | null;
  is_registered_professional: boolean | null;
  holds_constitutional_post: boolean | null;
};
export type MemberInput = Partial<MemberFields> & { nickname: string; relation: string };
export type Member = MemberFields & {
  id: string;
  nickname: string;
  relation: string;
  // Document code -> has it. A code that is missing was never answered ("not sure").
  documents: Record<string, boolean>;
};

export type DocumentInfo = {
  code: string;
  name_en: string;
  name_hi: string;
  household_level: boolean;
};

// GET /households/{id}/eligibility (backend/app/api/eligibility.py)
export type ReasonCode = "depends_on_exact_age" | "depends_on_exact_income";

export type SchemeSummary = {
  slug: string;
  name_en: string;
  name_hi: string | null;
  level: string;
  state: string | null;
  category: string;
  official_url: string;
  benefit_text_en: string | null;
  benefit_text_hi: string | null;
  deadline_start: string | null;
  deadline_end: string | null;
  // false: no human has checked this scheme against the official source yet.
  verified: boolean;
  verified_at: string | null;
};

export type RuleResult = {
  rule: Record<string, unknown>; // exactly as written in the scheme (see lib/rules.ts)
  fields: string[];
  matched_members: string[]; // nicknames whose facts decided an any_member rule
  fixable: boolean;
  reasons: ReasonCode[];
};

export type MissingDocument = {
  code: string;
  name_en: string;
  name_hi: string;
  how_to_get_en: string | null;
  how_to_get_hi: string | null;
  official_link: string | null;
  state: "no" | "not_answered";
};

export type SchemeResultStatus = "eligible" | "near_miss" | "unknown";

export type SchemeResult = {
  scheme: SchemeSummary;
  status: SchemeResultStatus;
  reasons: ReasonCode[];
  passed_rules: RuleResult[];
  failed_rules: RuleResult[];
  unknown_rules: RuleResult[];
  excluded_by: string[];
  missing_documents: MissingDocument[];
};

export type ExcludedScheme = {
  scheme: SchemeSummary;
  excluded_by: string[];
  failed_rules: RuleResult[];
};

export type MemberEligibility = {
  member_id: string;
  nickname: string;
  schemes: SchemeResult[];
  excluded: ExcludedScheme[];
  not_eligible_count: number;
};

export type Eligibility = {
  household_id: string;
  computed_on: string; // a date, "2026-11-03"
  members: MemberEligibility[];
  skipped_schemes: string[];
};
