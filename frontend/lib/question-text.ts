import type { Translate } from "./rule-text";

/**
 * The question a family is asked to settle an "unknown" result, in words.
 *
 * Two cases:
 * - A rule about one person ("Asha must be 60 or over"): the question names her, from
 *   `questions.<field>` ("Did Asha pay income tax last year?").
 * - A rule about the whole family (`any_member`, with or without `not`: "no one in the family pays
 *   income tax"): the question is about the family. A yes/no fact is asked as "anyone" ("Did
 *   anyone in your family pay income tax last year?"), because one yes from any member settles
 *   it; a "what" fact is asked of everyone ("What is the main work of everyone in your family?").
 *   Those whole sentences are in `familyQuestions.<field>`. Pasting "everyone in your family" into
 *   the one-person sentence got the yes/no ones wrong ("Did everyone ... pay income tax?" asks
 *   for the opposite of what the rule needs).
 * A fact with no family sentence falls back to the one-person sentence with "everyone".
 */
export function questionText(
  translate: Translate,
  need: { field: string; familyWide: boolean },
  context: { memberName: string; everyone: string; documentName: (code: string) => string },
): string {
  const { field, familyWide } = need;
  const isDocument = field.startsWith("has_");
  const document = isDocument ? context.documentName(field.slice(4)) : "";

  if (familyWide) {
    const key = `familyQuestions.${isDocument ? "document" : field}`;
    const sentence = translate(key, { document });
    if (sentence !== key) return sentence; // a missing message comes back as its own key
  }
  const name = familyWide ? context.everyone : context.memberName;
  return isDocument
    ? translate("questions.document", { name, document })
    : translate(`questions.${field}`, { name });
}
