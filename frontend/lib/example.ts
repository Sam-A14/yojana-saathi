import data from "./example-eligibility.json";
import type { DocumentInfo, Eligibility } from "./types";

// A made-up family, for the "See an example" pages (no sign-in, no server call). It is real rules
// engine output for an invented family, saved as a file (lib/example-eligibility.json), so the
// example screens are the real screens fed with fixed data. Nothing here is about any real person.
export const EXAMPLE_ELIGIBILITY = data as unknown as Eligibility;

export const EXAMPLE_DOCUMENTS: DocumentInfo[] = [
  { code: "aadhaar_card", name_en: "Aadhaar card", name_hi: "आधार कार्ड", household_level: false },
  { code: "income_certificate", name_en: "Income certificate", name_hi: "आय प्रमाण पत्र", household_level: false },
  { code: "spouse_death_certificate", name_en: "Death certificate of husband", name_hi: "पति का मृत्यु प्रमाण पत्र", household_level: false },
  { code: "bank_account_aadhaar_linked", name_en: "Bank account linked to Aadhaar", name_hi: "आधार से जुड़ा बैंक खाता", household_level: false },
  { code: "bpl_card", name_en: "BPL (below poverty line) card", name_hi: "बीपीएल (गरीबी रेखा से नीचे) कार्ड", household_level: true },
];

export const exampleSchemeHref = (memberId: string, slug: string) =>
  `/example/scheme/${slug}?member=${memberId}`;
