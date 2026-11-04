import type { Family } from "./types";

// The API needs the household id in the URL AND the token in a header, and nothing can find a
// household from its token alone. So the "family code" we show is both joined by a dot.
// See docs/decisions/012-family-code-format.md.
const UUID = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const TOKEN = "[A-Za-z0-9_-]{20,}"; // the API's tokens are 43 URL-safe characters
const CODE_IN_TEXT = new RegExp(`(${UUID})\\.(${TOKEN})`);
const CODE_ONLY = new RegExp(`^(${UUID})\\.(${TOKEN})$`);

export function makeFamilyCode(family: Family): string {
  return `${family.id}.${family.token}`;
}

/** Read a family code out of whatever the person pasted; null if there is none.
 *
 * Accepts the bare code, a code with spaces or line breaks inside it (a printed code is easy to
 * mistype), and the whole downloaded text file (the code is found inside it).
 */
export function parseFamilyCode(text: string): Family | null {
  // First: is the whole text one code, once spaces are removed? This must come before the search
  // below, which would stop at the first line break and keep only half of a wrapped token.
  const whole = CODE_ONLY.exec(text.replace(/\s+/g, ""));
  const found = whole ?? CODE_IN_TEXT.exec(text);
  return found ? { id: found[1].toLowerCase(), token: found[2] } : null;
}
