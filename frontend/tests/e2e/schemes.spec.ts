import { type Page } from "@playwright/test";
import { API } from "./fake-api";
import { expect, test } from "./fixtures";

// A scheme as GET /schemes sends it. Only what the API sends is ever shown.
const scheme = (over: Record<string, unknown>) => ({
  slug: "s",
  name_en: "A scheme",
  name_hi: null,
  level: "central",
  state: null,
  category: "farmer",
  official_url: "https://example.gov.in/",
  benefit_text_en: null,
  benefit_text_hi: null,
  deadline_start: null,
  deadline_end: null,
  verified: false,
  verified_at: null,
  ...over,
});

// Replace the fake server's answer for GET /schemes (a later route is tried first).
async function schemesAre(page: Page, list: unknown[]) {
  await page.route(`${API}/schemes`, (route) =>
    route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*" },
      contentType: "application/json",
      body: JSON.stringify(list),
    }),
  );
}

test("the public list shows every scheme from the API, grouped by category, with no sign-in", async ({ page, api }) => {
  await page.goto("/schemes");

  await expect(page.getByRole("heading", { level: 1, name: "All the schemes we check" })).toBeVisible();
  // Three schemes: one widow pension, and two with a category we have no words for ("Other").
  for (const group of ["Widow pension", "Other"]) {
    await expect(page.getByRole("heading", { level: 2, name: group })).toBeVisible();
  }
  await expect(page.getByRole("heading", { level: 2, name: "Farmers" })).toHaveCount(0); // no empty groups
  await expect(page.getByRole("heading", { level: 3 })).toHaveCount(3);
  const pension = page.getByRole("listitem").filter({ hasText: "Indira Gandhi National Widow Pension" }).first();
  await expect(pension.getByText("Not yet verified")).toBeVisible();
  const official = pension.getByRole("link", { name: "Official website" });
  await expect(official).toHaveAttribute("target", "_blank");
  await expect(official).toHaveAttribute("rel", /noopener/);
  await expect(page.getByRole("link", { name: "Check my family" })).toHaveAttribute("href", "/setup/basics");

  // Nothing about a family was asked of the server, and nobody had to sign in.
  expect(api.requests.map((r) => r.path).filter((p) => p !== "/health")).toEqual(["/schemes"]);
});

test("a scheme shows only the fields the API sent, and says nothing about the missing ones", async ({ page }) => {
  await schemesAre(page, [
    scheme({ slug: "bare", name_en: "Bare scheme" }),
    scheme({
      slug: "full",
      name_en: "Full scheme",
      level: "state",
      state: "UP",
      category: "education",
      benefit_text_en: "Pays for books.",
      deadline_start: "2026-04-01",
      deadline_end: "2027-03-31",
      verified: true,
      verified_at: "2026-09-15T00:00:00Z",
    }),
  ]);
  await page.goto("/schemes");

  const bare = page.getByRole("listitem").filter({ hasText: "Bare scheme" });
  await expect(bare.getByText("Central government scheme")).toBeVisible();
  await expect(bare).not.toContainText("Applications open");
  await expect(bare).not.toContainText("Last date to apply");
  await expect(bare.getByText("Not yet verified")).toBeVisible();
  await expect(bare.locator("p")).toHaveCount(0); // no benefit text was sent, so no paragraph is invented

  const full = page.getByRole("listitem").filter({ hasText: "Full scheme" });
  await expect(full).toContainText("Pays for books.");
  await expect(full).toContainText("State scheme: Uttar Pradesh");
  await expect(full).toContainText("Applications open: 1 April 2026");
  await expect(full).toContainText("Last date to apply: 31 March 2027");
  await expect(full).toContainText("Last checked on 15 September 2026");
  await expect(full).not.toContainText("Not yet verified");
});

test("a Hindi name is used when there is one, and the English name when there is not", async ({ page }) => {
  await schemesAre(page, [
    scheme({ slug: "a", name_en: "With Hindi", name_hi: "हिंदी नाम" }),
    scheme({ slug: "b", name_en: "English only", name_hi: null }),
  ]);
  await page.goto("/schemes");
  await page.getByRole("button", { name: "हिन्दी" }).click();

  await expect(page.getByRole("heading", { level: 1, name: "हम जो सभी योजनाएँ जाँचते हैं" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "हिंदी नाम" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "English only" })).toBeVisible();
  await expect(page.getByRole("link", { name: "आधिकारिक वेबसाइट" }).first()).toBeVisible();
});

test("when the schemes cannot be loaded there is a message and a way to try again", async ({ page, api }) => {
  api.offline = true;
  await page.goto("/schemes");
  await expect(page.getByText("We could not load the schemes just now.")).toBeVisible();

  api.offline = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 3 })).toHaveCount(3);
  await expect(page.getByText("We could not load the schemes just now.")).toHaveCount(0);
});

test("an empty catalogue says so instead of showing nothing", async ({ page }) => {
  await schemesAre(page, []);
  await page.goto("/schemes");
  await expect(page.getByText("There are no schemes to show yet.")).toBeVisible();
});

test("the home page links to the full list", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "See all schemes" }).click();
  await expect(page).toHaveURL(/\/schemes$/);
});
