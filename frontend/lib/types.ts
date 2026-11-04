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
