import { expect, test } from "@playwright/test";
import { makeFamilyCode, parseFamilyCode } from "../../lib/family-code";

const ID = "8f14e45f-ceea-467a-9575-3a2b5d0c1e11";
const TOKEN = "q3Zk-9_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789";

test("a code is the household id and the token joined by a dot", () => {
  expect(makeFamilyCode({ id: ID, token: TOKEN })).toBe(`${ID}.${TOKEN}`);
});

test("a bare code is read back", () => {
  expect(parseFamilyCode(`${ID}.${TOKEN}`)).toEqual({ id: ID, token: TOKEN });
});

test("spaces and line breaks around or inside the code are ignored", () => {
  expect(parseFamilyCode(`  ${ID}.${TOKEN}\n`)).toEqual({ id: ID, token: TOKEN });
  const wrapped = `${ID}.${TOKEN.slice(0, 20)}\n  ${TOKEN.slice(20)}`;
  expect(parseFamilyCode(wrapped)).toEqual({ id: ID, token: TOKEN });
});

test("the code is found inside the whole downloaded text file", () => {
  const file = `Yojana Saathi family code\n\n${ID}.${TOKEN}\n\nKeep this file safe.\n`;
  expect(parseFamilyCode(file)).toEqual({ id: ID, token: TOKEN });
});

test("the household id is lower-cased so it matches the API's ids", () => {
  expect(parseFamilyCode(`${ID.toUpperCase()}.${TOKEN}`)?.id).toBe(ID);
});

test.describe("things that are not family codes", () => {
  for (const [name, text] of Object.entries({
    empty: "",
    "just a token": TOKEN,
    "just an id": ID,
    "id with a short token": `${ID}.abc`,
    "not a uuid": `12345.${TOKEN}`,
    "a sentence": "my family code is lost",
  })) {
    test(name, () => expect(parseFamilyCode(text)).toBeNull());
  }
});
