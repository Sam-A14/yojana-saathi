// The letters shown in a person's round avatar: the first letter of the first and last word
// ("Asha Devi" -> "AD"; "Asha" -> "A").
//
// A "letter" is a grapheme (what a reader sees as one character), not name[0]. In Hindi, "कृ" is
// two code points (क + a vowel sign); taking the first code point would cut off the vowel sign.

const segmenter = typeof Intl !== "undefined" && "Segmenter" in Intl ? new Intl.Segmenter(undefined, { granularity: "grapheme" }) : null;

function firstLetter(word: string): string {
  if (segmenter) {
    const first = segmenter.segment(word)[Symbol.iterator]().next();
    if (!first.done) return first.value.segment;
  }
  return Array.from(word)[0] ?? ""; // very old browsers: whole code points at least
}

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const letters = words.length === 1 ? [words[0]] : [words[0], words[words.length - 1]];
  return letters.map(firstLetter).join("").toLocaleUpperCase();
}

/** Which of the five avatar colours a name gets. The same name always gets the same colour. */
export function avatarColour(name: string, colours = 5): number {
  let sum = 0;
  for (const char of name) sum = (sum * 31 + (char.codePointAt(0) ?? 0)) % 1000;
  return sum % colours;
}
