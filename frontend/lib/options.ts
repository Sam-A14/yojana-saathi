// The answers a family can choose from. Values are exactly what the API accepts
// (backend/app/rules/values.py); the words people see live in messages/.
export const AREA_TYPES = ["rural", "urban"] as const;
export const INCOME_BANDS = [
  "up_to_1_lakh",
  "1_to_2_lakh",
  "2_to_2_5_lakh",
  "2_5_to_3_lakh",
  "3_to_5_lakh",
  "5_to_8_lakh",
  "above_8_lakh",
] as const;
export const CATEGORIES = ["General", "SC", "ST", "OBC"] as const;

export const RELATIONS = [
  "self",
  "husband",
  "wife",
  "son",
  "daughter",
  "father",
  "mother",
  "grandfather",
  "grandmother",
  "brother",
  "sister",
  "other",
] as const;
// The API stores any text for a relation. Anything outside our list is shown as it was typed.
export const isRelation = (value: string): value is (typeof RELATIONS)[number] =>
  (RELATIONS as readonly string[]).includes(value);
export const GENDERS = ["male", "female", "other"] as const;
export const MARITAL_STATUSES = ["unmarried", "married", "widow", "divorced", "separated"] as const;
export const OCCUPATIONS = [
  "farmer",
  "agricultural_labourer",
  "student",
  "homemaker",
  "self_employed",
  "private_job",
  "government_job",
  "retired",
  "unemployed",
  "other",
] as const;
export const EDUCATIONS = [
  "none",
  "primary",
  "secondary",
  "senior_secondary",
  "graduate",
  "postgraduate",
] as const;

export const GOVT_EMPLOYEE = ["none", "group_d", "other"] as const;
export const PENSION_BANDS = ["none", "below_10k", "10k_plus"] as const;
