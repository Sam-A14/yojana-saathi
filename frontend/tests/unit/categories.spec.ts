import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { CATEGORIES, GROUP_ORDER, TOPIC_CATEGORIES } from "../../lib/categories";
import { en } from "../../messages/en";
import { hi } from "../../messages/hi";

// The category list exists in two places: data/scheme.schema.json (what a scheme file may say) and
// lib/categories.ts (what the pages know how to show). These tests fail if they drift apart, so a
// category can never be seeded and then land in "Other", or be mapped to a card and never exist.
const schema = JSON.parse(readFileSync(path.join(__dirname, "../../../data/scheme.schema.json"), "utf8"));
const inSchema: string[] = schema.properties.category.enum;

test("the schema's category list and the frontend's are the same", () => {
  expect([...CATEGORIES].sort()).toEqual([...inSchema].sort());
});

test("the Schemes page shows every category, and 'other' last", () => {
  expect([...GROUP_ORDER].sort()).toEqual([...CATEGORIES, "other"].sort());
  expect(GROUP_ORDER[GROUP_ORDER.length - 1]).toBe("other");
});

test("every landing card counts real categories, and every category belongs to one card", () => {
  const counted: string[] = Object.values(TOPIC_CATEGORIES).flat();
  expect(counted.sort()).toEqual([...CATEGORIES].sort()); // none missing, none counted twice
});

test("both languages have words for every category", () => {
  for (const messages of [en, hi]) {
    for (const category of [...CATEGORIES, "other"]) {
      expect((messages.categories as Record<string, string>)[category], category).toBeTruthy();
    }
  }
});
