import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// "What's new for your family": the daily job's news, shown on the dashboard, with "Mark as read".

const scheme = { slug: "ignoaps", name_en: "Indira Gandhi National Old Age Pension Scheme", name_hi: null };

function news(api: FakeApi) {
  api.alerts = [
    { id: 3, type: "rule_change", payload: { scheme, version_no: 2 }, created_at: "2026-11-03T03:00:00Z", read: false },
    { id: 2, type: "age_threshold", payload: { member: "Kamla", age: 60, year: 2027, schemes: [scheme] }, created_at: "2026-11-02T03:00:00Z", read: false },
    { id: 1, type: "new_scheme", payload: { member: "Asha", scheme }, created_at: "2026-10-01T03:00:00Z", read: true },
  ];
}

async function openDashboard(page: Page, api: FakeApi) {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Kamla", "Asha"]);
  await page.addInitScript(([key, value]) => localStorage.setItem(key, value), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/dashboard");
  return page.getByRole("region", { name: "What’s new for your family" });
}

test("the list shows the news in plain words, unread first, and counts what is new", async ({ page, api }) => {
  news(api);
  const list = await openDashboard(page, api);

  await expect(list.getByText("2 new")).toBeVisible();
  await expect(list.getByText("The rules of Indira Gandhi National Old Age Pension Scheme have changed.")).toBeVisible();
  await expect(list.getByText(/Kamla turns 60 in 2027\. We only know the year of birth/)).toBeVisible();
  await expect(list.getByText("Asha may now qualify for Indira Gandhi National Old Age Pension Scheme.")).toBeVisible();
  await expect(list.getByRole("button", { name: "Mark as read" })).toHaveCount(2); // the read one has none
});

test("marking one as read removes its button and lowers the count", async ({ page, api }) => {
  news(api);
  const list = await openDashboard(page, api);

  await list.getByRole("button", { name: "Mark as read" }).first().click();

  await expect(list.getByText("1 new")).toBeVisible();
  await expect(list.getByRole("button", { name: "Mark as read" })).toHaveCount(1);
  expect(api.alerts.find((a) => a.id === 3)?.read).toBe(true);
});

test("mark all as read clears the count and the buttons", async ({ page, api }) => {
  news(api);
  const list = await openDashboard(page, api);

  await list.getByRole("button", { name: "Mark all as read" }).click();

  await expect(list.getByText(/\d new/)).toHaveCount(0);
  await expect(list.getByRole("button", { name: "Mark as read" })).toHaveCount(0);
  expect(api.alerts.every((a) => a.read)).toBe(true);
});

test("with no news it says so, and it is in Hindi when the language is Hindi", async ({ page, api }) => {
  const list = await openDashboard(page, api);
  await expect(list.getByText("Nothing new yet.")).toBeVisible();

  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(page.getByRole("heading", { name: "आपके परिवार के लिए नया क्या है" })).toBeVisible();
});
