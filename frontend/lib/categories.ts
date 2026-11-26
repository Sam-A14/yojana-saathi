// The topic groups a scheme can be filed under. The list lives in data/scheme.schema.json (the seed
// loader and the extractor's validator enforce it); this copy is for the pages, and a unit test
// fails if the two ever differ.
export const CATEGORIES = ["education", "health", "housing", "family_welfare", "farmer", "widow_pension", "pension"] as const;
export type Category = (typeof CATEGORIES)[number];

// The order the groups appear on the Schemes page. "other" is anything we have no words for.
export const GROUP_ORDER = ["education", "farmer", "health", "housing", "family_welfare", "pension", "widow_pension", "other"] as const;

// Which backend categories each landing-page topic card counts. A card turns from "Coming soon"
// into a count and a link as soon as a seeded scheme has one of its categories.
export const TOPIC_CATEGORIES = {
  Education: ["education"],
  Agriculture: ["farmer"],
  Healthcare: ["health"],
  Women: ["widow_pension"],
  Seniors: ["pension"],
  Families: ["family_welfare", "housing"],
} as const satisfies Record<string, readonly Category[]>;
