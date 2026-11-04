import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

async function openFor(page: Page, api: FakeApi, person: string, scheme: string) {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Kamla", "Asha", "Ramesh", "Gudiya"]);
  await page.addInitScript(
    ([key, code]) => localStorage.setItem(key, JSON.stringify({ code, step: "done" })),
    [STORAGE_KEY, family.code],
  );
  await page.goto("/dashboard");
  await page.getByRole("region", { name: person, exact: true }).getByRole("link", { name: scheme }).first().click();
  await expect(page).toHaveURL(/\/scheme\/[^/?]+\?member=/);
  // Next.js keeps the dashboard in the page, hidden. Everything below is looked for inside the
  // scheme page's own <article>, which the dashboard does not have.
  const article = page.getByRole("article");
  await expect(article).toBeVisible();
  return { family, article };
}

// "What fits" and the other groups of the rule list.
const group = (article: ReturnType<Page["getByRole"]>, heading: string) =>
  article.locator("div", { has: article.page().getByRole("heading", { name: heading }) }).last();

test("a scheme that may fit: summary, ticked rules, missing papers, official link", async ({ page, api }) => {
  const { article } = await openFor(page, api, "Kamla", "Indira Gandhi National Widow Pension Scheme (IGNWPS)");

  await expect(page).toHaveURL(/\/scheme\/ignwps\?member=/);
  await expect(article.getByText("For Kamla")).toBeVisible();
  await expect(article.getByRole("heading", { level: 1 })).toContainText("Indira Gandhi National Widow Pension");
  await expect(article.getByText("Not yet verified: nobody has checked")).toBeVisible();
  await expect(article.getByText(/a monthly pension from the Centre for widows/)).toBeVisible();

  // Each rule in words, ticked (with a word for screen readers).
  const fits = group(article, "What fits");
  await expect(fits).toContainText("Gender: Female");
  await expect(fits).toContainText("Marital status: Widowed");
  await expect(fits).toContainText("Age: 40 or more");
  await expect(fits).toContainText("Has BPL (below poverty line) card");
  await expect(fits.getByText("Met:")).toHaveCount(4);

  // Papers still needed: one she said no to, one never answered.
  await expect(article.getByText("Death certificate of husband")).toBeVisible();
  await expect(article.getByText("You told us you do not have this.")).toBeVisible();
  await expect(article.getByText("We do not know yet if you have this.")).toBeVisible();

  const official = article.getByRole("link", { name: "Open the official website" });
  await expect(official).toHaveAttribute("href", "https://nsap.nic.in/");
  await expect(official).toHaveAttribute("target", "_blank");
  await expect(official).toHaveAttribute("rel", /noopener/);

  await article.getByRole("link", { name: "Back to your family’s schemes" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("a verified scheme shows its date, and a failed rule that can be fixed", async ({ page, api }) => {
  const { article } = await openFor(page, api, "Asha", "Example Scholarship");

  await expect(article.getByText("Last checked on 15 September 2026").first()).toBeVisible();
  await expect(article.getByText("Not yet verified")).toHaveCount(0);
  const unmet = group(article, "What does not fit");
  await expect(unmet).toContainText("Has Bank account linked to Aadhaar");
  await expect(unmet).toContainText("You can fix this");
  await expect(unmet.getByText("Not met:")).toHaveCount(1);
  const fits = group(article, "What fits");
  await expect(fits).toContainText("Age: 18 or more");
  await expect(fits).toContainText("At least one of these: Social category:");
  await expect(article.getByText("You told us you do not have this.")).toBeVisible();
});

test("an unknown rule is marked as not checked yet, with what would settle it", async ({ page, api }) => {
  const { article } = await openFor(page, api, "Asha", "Indira Gandhi National Widow Pension Scheme (IGNWPS)");

  const unchecked = group(article, "What we could not check yet");
  await expect(unchecked).toContainText("Age: 40 or more");
  await expect(unchecked.getByText("Not checked yet:")).toHaveCount(1);
  await expect(unchecked).toContainText("This depends on the exact age.");
});

test("a blocked scheme shows who is the cause and which rule", async ({ page, api }) => {
  const { article } = await openFor(page, api, "Kamla", "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)");

  await expect(article.getByRole("heading", { name: "Why it is not available" })).toBeVisible();
  await expect(article.getByText("Because of Ramesh:")).toBeVisible();
  await expect(article.getByText("No one in the family: Paid income tax last year")).toBeVisible();
  await expect(article.getByText("Not met:")).toHaveCount(1);
});

test("the page is in Hindi when the language is Hindi", async ({ page, api }) => {
  const { article } = await openFor(page, api, "Kamla", "Indira Gandhi National Widow Pension Scheme (IGNWPS)");

  await page.getByRole("button", { name: "हिन्दी" }).click();

  await expect(article.getByRole("heading", { name: "जो ठीक बैठता है" })).toBeVisible();
  await expect(article.getByText("लिंग: महिला")).toBeVisible();
  await expect(article.getByText("पति का मृत्यु प्रमाण पत्र")).toBeVisible();
  await expect(article.getByRole("link", { name: "सरकारी वेबसाइट खोलें" })).toBeVisible();
});

test("opening a scheme without saying for whom asks to start from the family page", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Kamla"]);
  await page.addInitScript(
    ([key, code]) => localStorage.setItem(key, JSON.stringify({ code, step: "done" })),
    [STORAGE_KEY, family.code],
  );

  await page.goto("/scheme/ignwps");

  await expect(page.getByText("Open a scheme from your family’s page")).toBeVisible();
});
