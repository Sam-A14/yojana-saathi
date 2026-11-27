import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// The bug: Household > Edit > Save worked once, but the next time the edit page was opened its
// button said "Saving…" (disabled) for good, with no request sent. Next.js keeps a page you leave
// alive, hidden, with its state, and the page never cleared "saving" after a good save.

const patches = (api: FakeApi) => api.requests.filter((r) => r.method === "PATCH");

async function openEdit(page: Page, api: FakeApi) {
  const family = api.seedHousehold({ state: "UP", district: "Agra", area_type: "rural", income_band: "1_to_2_lakh", category: "OBC", is_bpl: null });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/household/edit");
  await expect(page.getByLabel("District (optional)")).toHaveValue("Agra");
  return family;
}

const bplQuestion = (page: Page) => page.getByRole("group", { name: "Is your family on the BPL (Below Poverty Line) list?" });

test("Save sends one PATCH and the page reaches the saved state within 2 seconds", async ({ page, api }) => {
  const family = await openEdit(page, api);

  await page.getByLabel("District (optional)").fill("Kanpur");
  await bplQuestion(page).getByLabel("Yes", { exact: true }).check();
  const clicked = Date.now();
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 2000 });
  expect(Date.now() - clicked).toBeLessThan(2000);
  expect(patches(api)).toHaveLength(1); // exactly one save, not zero and not two
  expect(patches(api)[0].body).toMatchObject({ district: "Kanpur", is_bpl: true });
  expect(api.households.get(family.id)!.fields).toMatchObject({ district: "Kanpur", is_bpl: true });
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
});

test("coming back to the edit page after a good save is not stuck on Saving…", async ({ page, api }) => {
  const family = await openEdit(page, api);
  await page.getByLabel("District (optional)").fill("Kanpur");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 2000 });

  await page.getByRole("link", { name: "Edit household details" }).click(); // the person opens it again

  await expect(page).toHaveURL(/\/household\/edit$/);
  const save = page.getByRole("button", { name: "Save changes" });
  await expect(save).toBeVisible();
  await expect(save).toBeEnabled();
  await expect(page.getByRole("button", { name: "Saving…" })).toHaveCount(0);

  // and a second save works, with one more PATCH
  await page.getByLabel("District (optional)").fill("Lucknow");
  await bplQuestion(page).getByLabel("No", { exact: true }).check();
  await save.click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 2000 });
  expect(patches(api)).toHaveLength(2);
  expect(api.households.get(family.id)!.fields).toMatchObject({ district: "Lucknow", is_bpl: false });
});

test("it can be done again and again", async ({ page, api }) => {
  const family = await openEdit(page, api);
  for (const district of ["A", "B", "C"]) {
    await page.getByLabel("District (optional)").fill(district);
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 2000 });
    await page.getByRole("link", { name: "Edit household details" }).click();
    await expect(page.getByRole("button", { name: "Save changes" })).toBeEnabled();
  }
  expect(patches(api)).toHaveLength(3);
  expect(api.households.get(family.id)!.fields).toMatchObject({ district: "C" });
});

test("a failed save shows its error and is not carried back as 'Saving…' either", async ({ page, api }) => {
  await openEdit(page, api);
  api.offline = true;
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText(/could not reach the server/i)).toBeVisible();
  await expect(page.getByRole("button", { name: "Save changes" })).toBeEnabled(); // the error path was always fine
});

test("the setup screens are not stuck on Saving… when you go back to them", async ({ page, api }) => {
  const family = api.seedHousehold({ state: "UP", area_type: "rural", income_band: "1_to_2_lakh" });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/setup/documents");
  await page.getByRole("button", { name: "Save and continue" }).click();
  await expect(page).toHaveURL(/\/setup\/exclusions$/, { timeout: 2000 });

  await page.goBack(); // to the papers screen

  await expect(page).toHaveURL(/\/setup\/documents$/);
  await expect(page.getByRole("button", { name: "Save and continue" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Saving…" })).toHaveCount(0);
});
