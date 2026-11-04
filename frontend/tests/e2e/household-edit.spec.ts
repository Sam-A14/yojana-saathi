import { type Page } from "@playwright/test";
import { FakeApi, MISSING_HOME } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

const HOME = { state: "UP", district: "Lucknow", area_type: "rural", income_band: "1_to_2_lakh", category: "OBC" };

async function openDashboard(page: Page, api: FakeApi, members = ["Asha"]) {
  const family = api.seedHousehold(HOME);
  api.seedMembers(family.id, members);
  await page.addInitScript(
    ([key, code]) => localStorage.setItem(key, JSON.stringify({ code, step: "done" })),
    [STORAGE_KEY, family.code],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("region", { name: members[0], exact: true })).toBeVisible();
  return family;
}

test("the dashboard links to the edit screen, which starts from the saved answers", async ({ page, api }) => {
  await openDashboard(page, api);

  await page.getByRole("link", { name: "Edit household details" }).click();

  await expect(page).toHaveURL(/\/household\/edit$/);
  await expect(page.getByRole("heading", { name: "Household details" })).toBeVisible();
  await expect(page.getByLabel("State")).toHaveValue("UP");
  await expect(page.getByLabel("District (optional)")).toHaveValue("Lucknow");
  await expect(page.getByLabel("Village (rural)")).toBeChecked();
  await expect(page.getByLabel("Yearly income of the whole family")).toHaveValue("1_to_2_lakh");
  await expect(page.getByLabel("Social category")).toHaveValue("OBC");
});

test("saving sends only the household, with the token, and the dashboard asks again", async ({ page, api }) => {
  const family = await openDashboard(page, api);
  const asked = () => api.requests.filter((r) => r.path.endsWith("/eligibility")).length;
  expect(asked()).toBe(1);
  await page.getByRole("link", { name: "Edit household details" }).click();

  await page.getByLabel("District (optional)").fill("Kanpur");
  await page.getByLabel("Not sure", { exact: true }).check(); // area: "not sure" clears the answer
  await page.getByLabel("Yearly income of the whole family").selectOption("2_to_2_5_lakh");
  await page.getByLabel("Social category").selectOption({ label: "Prefer not to say" });
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  const patches = api.requests.filter((r) => r.method === "PATCH");
  expect(patches).toEqual([
    expect.objectContaining({
      path: `/households/${family.id}`,
      authorization: `Bearer ${family.token}`,
      // Everything on the form is sent; null means "no answer" (the API clears it).
      body: { state: "UP", district: "Kanpur", area_type: null, income_band: "2_to_2_5_lakh", category: null },
    }),
  ]);
  expect(api.households.get(family.id)!.fields).toMatchObject({
    district: "Kanpur", area_type: null, income_band: "2_to_2_5_lakh", category: null,
  });
  expect(api.households.get(family.id)!.members).toHaveLength(1); // nothing else was touched
  await expect.poll(asked).toBeGreaterThanOrEqual(2); // the new answers are checked again
});

test("going back without saving changes nothing", async ({ page, api }) => {
  await openDashboard(page, api);
  await page.getByRole("link", { name: "Edit household details" }).click();
  await page.getByLabel("District (optional)").fill("Somewhere else");

  await page.getByRole("link", { name: "Back without saving" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  expect(api.requests.filter((r) => r.method === "PATCH")).toHaveLength(0);
});

test("unknown questions about state, area and income lead to the edit screen", async ({ page, api }) => {
  api.fixture = MISSING_HOME;
  await openDashboard(page, api);
  const item = page.getByRole("region", { name: "Asha", exact: true }).getByRole("listitem").filter({ hasText: "Example Local Scheme" });

  for (const question of [
    "Which state does your family live in?",
    "Does your family live in a village or a town?",
    "How much does your family earn in a year?",
  ]) {
    const row = item.getByRole("listitem").filter({ hasText: question });
    await expect(row.getByRole("link", { name: "Answer this" })).toHaveAttribute("href", "/household/edit");
  }

  // The same questions on the scheme page lead there too.
  await item.getByRole("link", { name: "Example Local Scheme" }).click();
  const article = page.getByRole("article");
  await expect(article).toBeVisible();
  await expect(article.getByRole("link", { name: "Answer this" })).toHaveCount(3);
  await article.getByRole("link", { name: "Answer this" }).first().click();
  await expect(page).toHaveURL(/\/household\/edit$/);
});

test("a lost connection can be retried, and a code that no longer works leads to resume", async ({ page, api }) => {
  await openDashboard(page, api);
  api.offline = true;
  await page.getByRole("link", { name: "Edit household details" }).click();
  await expect(page.getByText(/We could not reach the server/)).toBeVisible();

  api.offline = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByLabel("District (optional)")).toHaveValue("Lucknow");

  api.offline = true;
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText(/We could not reach the server/)).toBeVisible();
  expect(api.requests.filter((r) => r.method === "PATCH")).toHaveLength(0);
});

test("the edit screen speaks Hindi", async ({ page, api }) => {
  await openDashboard(page, api);
  await page.getByRole("link", { name: "Edit household details" }).click();

  await page.getByRole("button", { name: "हिन्दी" }).click();

  await expect(page.getByRole("heading", { name: "घर की जानकारी" })).toBeVisible();
  await expect(page.getByRole("button", { name: "बदलाव सहेजें" })).toBeVisible();
});

test("without a saved family there is nothing to edit", async ({ page }) => {
  await page.goto("/household/edit");

  await expect(page.getByText("We could not find a saved family on this phone.")).toBeVisible();
});
