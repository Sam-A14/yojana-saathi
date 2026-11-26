import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

// Reads the real colours from globals.css and measures WCAG contrast for every pair that appears
// on screen, in light and in dark. If someone edits a colour and a pair drops under its target,
// this fails. The target is 7:1 (AAA) for reading text, 4.5:1 (AA) for button, chip and link text,
// 3:1 for the borders of inputs. Gold (--accent) is only ever a fill, so it is paired with its dark text.
const css = readFileSync(join(__dirname, "../../app/globals.css"), "utf8");

function tokens(selector: string, from = 0): Record<string, string> {
  const start = css.indexOf(selector, from);
  const open = css.indexOf("{", start);
  const body = css.slice(open + 1, css.indexOf("}", open));
  const result: Record<string, string> = {};
  for (const match of body.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)) result[match[1]] = match[2];
  return result;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const ratio = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const light = tokens(":root");
const dark = { ...light, ...tokens(':root[data-theme="dark"]') };

// [text colour, background, minimum ratio]
const PAIRS: [string, string, number][] = [
  ["ink", "bg", 7], ["ink", "surface", 7], ["ink", "soft", 7],
  ["muted", "bg", 7], ["muted", "surface", 7], ["muted", "soft", 7],
  ["line", "bg", 3], ["line", "surface", 3],
  ["primary", "bg", 7], ["primary", "surface", 7], ["primary", "soft", 7], ["primary", "primary-soft", 7],
  ["on-primary", "primary", 7], ["on-primary", "primary-hover", 7],
  ["teal", "bg", 7], ["teal", "surface", 7], ["teal", "teal-soft", 4.5],
  ["on-accent", "accent", 7], ["on-accent", "accent-hover", 7],
  ["accent-ink", "bg", 7], ["accent-ink", "surface", 7],
  ["on-hero", "hero", 7], ["on-hero-muted", "hero", 7], ["accent", "hero", 4.5],
  ["danger", "bg", 7], ["danger", "danger-bg", 4.5],
  ["ok-fg", "ok-bg", 7], ["close-fg", "close-bg", 7], ["ask-fg", "ask-bg", 7], ["block-fg", "block-bg", 7],
  ["av1-fg", "av1-bg", 7], ["av2-fg", "av2-bg", 7], ["av3-fg", "av3-bg", 7], ["av4-fg", "av4-bg", 7], ["av5-fg", "av5-bg", 7],
  ...[1, 2, 3, 4, 5, 6].map((n): [string, string, number] => [`cat${n}-fg`, `cat${n}-bg`, 7]),
];

for (const [theme, colours] of [["light", light], ["dark", dark]] as const) {
  test(`every text and border pair meets its contrast target in ${theme}`, () => {
    const failures = PAIRS.filter(([fg, bg, min]) => ratio(colours[fg], colours[bg]) < min).map(
      ([fg, bg, min]) => `${fg} on ${bg}: ${ratio(colours[fg], colours[bg]).toFixed(2)} (needs ${min})`,
    );
    expect(failures).toEqual([]);
  });
}
