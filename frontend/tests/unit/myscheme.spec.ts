import { expect, test } from "@playwright/test";
import { categoryWords, MYSCHEME_KEYWORD_PARAM, MYSCHEME_SEARCH_URL, mySchemeUrl } from "../../lib/myscheme";
import { CATEGORIES } from "../../lib/categories";

test.describe("the link out to myScheme", () => {
  test("no words: myScheme's plain search page", () => {
    expect(mySchemeUrl()).toBe("https://www.myscheme.gov.in/search");
    expect(mySchemeUrl([])).toBe(MYSCHEME_SEARCH_URL);
    expect(mySchemeUrl(["", "  "])).toBe(MYSCHEME_SEARCH_URL);
  });

  test("the words go in one keyword, safely written for an address", () => {
    expect(mySchemeUrl(["Pension", "Uttar Pradesh"])).toBe(`${MYSCHEME_SEARCH_URL}?${MYSCHEME_KEYWORD_PARAM}=Pension+Uttar+Pradesh`);
    const url = new URL(mySchemeUrl(["Women & child", "a=b"]));
    expect(url.searchParams.get(MYSCHEME_KEYWORD_PARAM)).toBe("Women & child a=b"); // nothing escapes the keyword
    expect([...url.searchParams.keys()]).toEqual([MYSCHEME_KEYWORD_PARAM]);
  });

  test("every topic group has search words, and 'Uttar Pradesh' is added only with a state scheme", () => {
    for (const group of CATEGORIES) {
      const central = categoryWords(group, false);
      expect(central.length, group).toBe(1);
      expect(categoryWords(group, true), group).toEqual([...central, "Uttar Pradesh"]);
    }
  });

  test("a group with no words (other) has no link", () => {
    expect(categoryWords("other", true)).toEqual([]);
    expect(categoryWords("anything-else", false)).toEqual([]);
  });
});
