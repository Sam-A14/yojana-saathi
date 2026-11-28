import { readFileSync } from "node:fs";
import path from "node:path";
import { type Page } from "@playwright/test";
import { FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// Every answer about the home that a scheme rule can use must be changeable on /household/edit, and
// a change must reach the schemes. PMAY-Gramin is the example: it needs a village and a kutcha
// house (or none), so changing either answer must make it appear or disappear.

const PMAY_G = "Pradhan Mantri Awaas Yojana - Gramin";
const HOME = { state: "UP", district: "Lucknow", income_band: "1_to_2_lakh", category: "OBC" };
const AREA = "Where do you live?";
const HOUSE = "What kind of house does your family live in?";

async function openDashboard(page: Page, api: FakeApi, fields: Record<string, unknown>) {
  const family = api.seedHousehold({ ...HOME, ...fields });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  return family;
}

// PMAY-Gramin is about the whole family, so the dashboard shows it once, in its own section.
const family = (page: Page) => page.getByRole("region", { name: "For the whole family" });
const pmayG = (page: Page) => family(page).getByRole("listitem").filter({ hasText: PMAY_G });

async function openEdit(page: Page) {
  await page.getByRole("link", { name: "Edit household details" }).click();
  await expect(page).toHaveURL(/\/household\/edit$/);
  await expect(page.getByRole("heading", { name: "Household details" })).toBeVisible();
}

async function saveAndWait(page: Page) {
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
}

test.describe("changing the answers about the home changes the schemes", () => {
  test("PMAY-Gramin appears when the family says village and kutcha house, and goes when either changes", async ({ page, api }) => {
    const family = await openDashboard(page, api, { area_type: "urban", house_type: "pucca" });
    await expect(pmayG(page)).toHaveCount(0);

    // Both answers changed on the edit screen.
    await openEdit(page);
    await page.getByRole("group", { name: AREA }).getByLabel("Village (rural)").check();
    await page.getByRole("group", { name: HOUSE }).getByLabel("A kutcha house (mud, thatch, bamboo)").check();
    await saveAndWait(page);

    expect(api.households.get(family.id)!.fields).toMatchObject({ area_type: "rural", house_type: "kutcha" });
    await expect(pmayG(page)).toHaveCount(1);
    await expect(pmayG(page)).toContainText("May qualify");

    // Only the house changes: a pucca house is a no.
    await openEdit(page);
    await page.getByRole("group", { name: HOUSE }).getByLabel("A pucca house (brick, cement)").check();
    await saveAndWait(page);
    expect(api.households.get(family.id)!.fields).toMatchObject({ area_type: "rural", house_type: "pucca" });
    await expect(pmayG(page)).toHaveCount(0);

    // Back to no house, then only the area changes: a town is a no.
    await openEdit(page);
    await page.getByRole("group", { name: HOUSE }).getByLabel("We have no house of our own").check();
    await saveAndWait(page);
    await expect(pmayG(page)).toHaveCount(1);

    await openEdit(page);
    await page.getByRole("group", { name: AREA }).getByLabel("Town or city (urban)").check();
    await saveAndWait(page);
    expect(api.households.get(family.id)!.fields).toMatchObject({ area_type: "urban", house_type: "no_house" });
    await expect(pmayG(page)).toHaveCount(0);
  });

  test("both answers are sent in the one save, and a saved answer shows again when the form is reopened", async ({ page, api }) => {
    const family = await openDashboard(page, api, { area_type: "rural", house_type: "kutcha" });

    await openEdit(page);
    await page.getByRole("group", { name: AREA }).getByLabel("Town or city (urban)").check();
    await page.getByRole("group", { name: HOUSE }).getByLabel("A pucca house (brick, cement)").check();
    await saveAndWait(page);
    const patches = api.requests.filter((r) => r.method === "PATCH" && r.path === `/households/${family.id}`);
    expect(patches.at(-1)!.body).toMatchObject({ area_type: "urban", house_type: "pucca" });

    await openEdit(page);
    await expect(page.getByRole("group", { name: AREA }).getByLabel("Town or city (urban)")).toBeChecked();
    await expect(page.getByRole("group", { name: HOUSE }).getByLabel("A pucca house (brick, cement)")).toBeChecked();
  });

  test("the form shows the saved answers when you come back, not the ones it first loaded", async ({ page, api }) => {
    const family = await openDashboard(page, api, { area_type: "rural", house_type: "kutcha" });
    await openEdit(page);
    await expect(page.getByRole("group", { name: AREA }).getByLabel("Village (rural)")).toBeChecked();
    await page.getByRole("link", { name: "Back without saving" }).click();
    await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();

    // The answers change somewhere else (another phone, another tab).
    api.households.get(family.id)!.fields.area_type = "urban";
    api.households.get(family.id)!.fields.house_type = "pucca";

    await openEdit(page);
    await expect(page.getByRole("group", { name: AREA }).getByLabel("Town or city (urban)")).toBeChecked();
    await expect(page.getByRole("group", { name: HOUSE }).getByLabel("A pucca house (brick, cement)")).toBeChecked();
    // Saving without touching them must not put the old answers back.
    await saveAndWait(page);
    expect(api.households.get(family.id)!.fields).toMatchObject({ area_type: "urban", house_type: "pucca" });
  });
});

// The guard for "every household answer used by a rule can be edited here": the rules engine's list
// of household facts (backend/app/rules/fields.py) must be exactly the facts this test finds a
// question for on the edit screen. Add a household fact to the engine and this fails until the
// edit form asks it.
const QUESTIONS: Record<string, string | RegExp> = {
  state: "State",
  district: "District (optional)",
  area_type: AREA,
  income_band_max: "Yearly income of the whole family",
  category: "Social category",
  house_type: HOUSE,
  is_bpl: /Is your family on the BPL/,
};

function engineHouseholdFields(): string[] {
  const source = readFileSync(path.resolve(__dirname, "../../../backend/app/rules/fields.py"), "utf8");
  const block = source.match(/HOUSEHOLD_FIELDS = frozenset\(\s*\{([^}]*)\}/);
  if (!block) throw new Error("HOUSEHOLD_FIELDS not found in backend/app/rules/fields.py");
  return [...block[1].matchAll(/"([a-z_]+)"/g)].map((m) => m[1]).sort();
}

test("every household fact a rule can use has a question on the edit screen", async ({ page, api }) => {
  expect(engineHouseholdFields()).toEqual(Object.keys(QUESTIONS).sort());

  await openDashboard(page, api, { area_type: "rural", house_type: "kutcha" });
  await openEdit(page);
  for (const [field, question] of Object.entries(QUESTIONS)) {
    const control = page.getByRole("group", { name: question }).or(page.getByLabel(question));
    await expect(control.first(), `no question for ${field}`).toBeVisible();
  }
});
