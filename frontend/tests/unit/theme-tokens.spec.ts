import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

// The dark colours are written twice in globals.css (see the comment there): once for a person who
// chose Dark and once for "Match device" on a dark phone. These tests keep the two copies identical
// and make sure no colour is forgotten in dark.
const css = readFileSync(join(__dirname, "../../app/globals.css"), "utf8");

// The declarations inside the `{ }` of the first `selector` found after position `from`.
function declarations(selector: string, from = 0): string[] {
  const start = css.indexOf(selector, from);
  expect(start, `${selector} is in globals.css`).toBeGreaterThan(-1);
  const open = css.indexOf("{", start + selector.length);
  const body = css.slice(open + 1, css.indexOf("}", open));
  return body.split(";").map((d) => d.replace(/\s+/g, " ").trim()).filter(Boolean);
}

const name = (declaration: string) => declaration.split(":")[0].trim();
const withoutScheme = (list: string[]) => list.filter((d) => !d.startsWith("color-scheme"));

test("the dark colours for 'Dark' and for 'Match device' are the same", () => {
  const dark = withoutScheme(declarations(':root[data-theme="dark"]'));
  const media = css.indexOf("@media (prefers-color-scheme: dark)");
  const viaDevice = withoutScheme(declarations(':root[data-theme="device"]', media));
  expect(viaDevice).toEqual(dark);
  expect(dark.length).toBeGreaterThan(30);
});

test("every colour token has a dark value, except the ones used only on the always-dark hero", () => {
  const light = declarations(":root").map(name).filter((n) => n.startsWith("--") && !n.startsWith("--shadow"));
  const dark = new Set(declarations(':root[data-theme="dark"]').map(name));
  const heroOnly = ["--on-hero", "--on-hero-muted"];
  expect(light.filter((n) => !dark.has(n) && !heroOnly.includes(n))).toEqual([]);
});
