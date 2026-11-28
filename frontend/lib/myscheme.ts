// A way out to myScheme (the government's own scheme search) for families who want to look beyond
// the schemes we check. A link only: nothing is fetched from myScheme and no data is copied.

export const MYSCHEME_SEARCH_URL = "https://www.myscheme.gov.in/search";
// The name of the address parameter that holds what myScheme's search box would hold. Kept in one
// place: if myScheme names it differently, this is the only line to change.
export const MYSCHEME_KEYWORD_PARAM = "keyword";

// What to search for, by the topic groups of the Schemes page (the words a person would type).
const SEARCH_WORDS: Record<string, string> = {
  education: "Education scholarship",
  farmer: "Farmer",
  health: "Health",
  housing: "Housing",
  family_welfare: "Women and child",
  widow_pension: "Widow pension",
  pension: "Pension",
};

/** The search address for these words ("" words: myScheme's plain search page). */
export function mySchemeUrl(words: string[] = []): string {
  const keyword = words.map((w) => w.trim()).filter(Boolean).join(" ");
  if (!keyword) return MYSCHEME_SEARCH_URL;
  return `${MYSCHEME_SEARCH_URL}?${new URLSearchParams({ [MYSCHEME_KEYWORD_PARAM]: keyword }).toString()}`;
}

/** The words for one topic group. "Uttar Pradesh" is added when the group has a state scheme of
 * ours: that is where a UP family may find more state schemes. A group with no words (such as
 * "other") has none. */
export function categoryWords(group: string, hasStateScheme: boolean): string[] {
  const topic = SEARCH_WORDS[group];
  if (!topic) return [];
  return hasStateScheme ? [topic, "Uttar Pradesh"] : [topic];
}
