import { expect, test } from "@playwright/test";
import { sourceCredit } from "../../lib/source-credit";

// The "Source:" line on a scheme page: myScheme pages are credited to myScheme, any other address
// to its own site, and anything that is not a web address gets no line at all.

test("a myScheme page is credited to myScheme and linked", () => {
  expect(sourceCredit("https://www.myscheme.gov.in/schemes/pmay-g")).toEqual({
    kind: "myscheme",
    href: "https://www.myscheme.gov.in/schemes/pmay-g",
  });
  expect(sourceCredit("https://myscheme.gov.in/schemes/x")?.kind).toBe("myscheme");
});

test("another site is credited as an official site, by its host without www", () => {
  expect(sourceCredit("https://www.pmkisan.gov.in/Home.aspx")).toEqual({
    kind: "official",
    href: "https://www.pmkisan.gov.in/Home.aspx",
    host: "pmkisan.gov.in",
  });
});

test("a look-alike host is not myScheme", () => {
  expect(sourceCredit("https://myscheme.gov.in.evil.example/schemes/x")?.kind).toBe("official");
});

test("no address, a bad address or a non-web address gives no line", () => {
  for (const bad of [undefined, null, "", "not a url", "javascript:alert(1)", "file:///etc/passwd"]) {
    expect(sourceCredit(bad)).toBeNull();
  }
});
