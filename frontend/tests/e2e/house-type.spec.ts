import { type Page } from "@playwright/test";
import { FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// "What kind of house does your family live in?" is one more home question: no house of our own,
// a kutcha house or a pucca house. "Not sure" is saved as null (unknown), never as a kind of house.

const HOME = { state: "UP", district: "Lucknow", area_type: "rural", income_band: "1_to_2_lakh", category: "OBC" };
const QUESTION = "What kind of house does your family live in?";

async function openEdit(page: Page, api: FakeApi, fields: Record<string, unknown> = {}) {
  const family = api.seedHousehold({ ...HOME, ...fields });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/household/edit");
  await expect(page.getByRole("heading", { name: "Household details" })).toBeVisible();
  return family;
}

const patches = (api: FakeApi) => api.requests.filter((r) => r.method === "PATCH");

test.describe("the house question", () => {
  test("starts on Not sure for a family that never answered", async ({ page, api }) => {
    await openEdit(page, api);

    const group = page.getByRole("group", { name: QUESTION });
    await expect(group.getByLabel("Not sure")).toBeChecked();
    await expect(group.getByLabel("We have no house of our own")).not.toBeChecked();
  });

  test("starts from the saved answer", async ({ page, api }) => {
    await openEdit(page, api, { house_type: "kutcha" });

    await expect(page.getByRole("group", { name: QUESTION }).getByLabel("A kutcha house (mud, thatch, bamboo)")).toBeChecked();
  });

  test("a chosen kind of house is sent with the household", async ({ page, api }) => {
    const family = await openEdit(page, api);

    await page.getByRole("group", { name: QUESTION }).getByLabel("A pucca house (brick, cement)").check();
    await page.getByRole("button", { name: "Save changes" }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    expect(patches(api)[0].body).toMatchObject({ house_type: "pucca" });
    expect(api.households.get(family.id)!.fields).toMatchObject({ house_type: "pucca" });
  });

  test("Not sure clears an old answer: null is sent, never a guess", async ({ page, api }) => {
    const family = await openEdit(page, api, { house_type: "no_house" });

    await page.getByRole("group", { name: QUESTION }).getByLabel("Not sure").check();
    await page.getByRole("button", { name: "Save changes" }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    expect(patches(api)[0].body).toMatchObject({ house_type: null });
    expect(api.households.get(family.id)!.fields).toMatchObject({ house_type: null });
  });

  test("the words are in Hindi too", async ({ page, api }) => {
    await openEdit(page, api);
    await page.getByRole("button", { name: "हिन्दी" }).click();

    const group = page.getByRole("group", { name: "आपका परिवार किस तरह के घर में रहता है?" });
    await expect(group.getByLabel("हमारा अपना कोई घर नहीं है")).toBeVisible();
    await expect(group.getByLabel("कच्चा घर (मिट्टी, फूस, बाँस)")).toBeVisible();
    await expect(group.getByLabel("पक्का घर (ईंट, सीमेंट)")).toBeVisible();
  });
});
