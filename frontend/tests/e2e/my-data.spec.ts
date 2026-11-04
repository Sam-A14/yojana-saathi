import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

async function openDashboard(page: Page, api: FakeApi) {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, code]) => {
      // Runs on every page load, so only set it the first time: a test that clears it must stay cleared.
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, JSON.stringify({ code, step: "done" }));
      }
    },
    [STORAGE_KEY, family.code],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Your data" })).toBeVisible();
  return family;
}

const stored = (page: Page) => page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY);
const deletes = (api: FakeApi) => api.requests.filter((r) => r.method === "DELETE");

test.describe("Delete my data", () => {
  test("asks first, and keeping the data changes nothing", async ({ page, api }) => {
    await openDashboard(page, api);

    await page.getByRole("button", { name: "Delete my data" }).click();
    await expect(page.getByRole("alertdialog", { name: "Delete everything?" })).toContainText("cannot be undone");
    await page.getByRole("button", { name: "No, keep my data" }).click();

    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    expect(deletes(api)).toHaveLength(0);
    expect(await stored(page)).not.toBeNull();
  });

  test("deletes the family on the server, then forgets this phone", async ({ page, api }) => {
    const family = await openDashboard(page, api);

    await page.getByRole("button", { name: "Delete my data" }).click();
    await page.getByRole("button", { name: "Yes, delete my data" }).click();

    await expect(page).toHaveURL(/\/deleted$/);
    await expect(page.getByRole("heading", { name: "Your data was deleted" })).toBeVisible();
    expect(deletes(api)).toEqual([
      expect.objectContaining({ path: `/households/${family.id}`, authorization: `Bearer ${family.token}` }),
    ]);
    expect(api.households.has(family.id)).toBe(false);
    expect(await stored(page)).toBeNull();
  });

  test("if the server cannot be reached, nothing is forgotten and the family can try again", async ({ page, api }) => {
    const family = await openDashboard(page, api);
    await page.getByRole("button", { name: "Delete my data" }).click();

    api.offline = true;
    await page.getByRole("button", { name: "Yes, delete my data" }).click();
    await expect(page.getByText(/We could not reach the server/)).toBeVisible();
    expect(await stored(page)).not.toBeNull();

    api.offline = false;
    await page.getByRole("button", { name: "Yes, delete my data" }).click();
    await expect(page).toHaveURL(/\/deleted$/);
    expect(api.households.has(family.id)).toBe(false);
  });
});

test.describe("Forget this device", () => {
  test("asks first, with a reminder to keep the family code, and keeping it changes nothing", async ({ page, api }) => {
    await openDashboard(page, api);

    await page.getByRole("button", { name: "Forget this device" }).click();
    const dialog = page.getByRole("alertdialog", { name: "Remove the family code from this phone?" });
    await expect(dialog).toContainText("Your family’s information stays on our server.");
    await expect(dialog).toContainText("Keep your family code safe, for example on the printed paper.");
    await page.getByRole("button", { name: "No, keep it here" }).click();

    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    expect(await stored(page)).not.toBeNull();
  });

  test("clears this phone only: the family stays on the server and opens again with its code", async ({ page, api }) => {
    const family = await openDashboard(page, api);

    await page.getByRole("button", { name: "Forget this device" }).click();
    await page.getByRole("button", { name: "Yes, forget this phone" }).click();

    await expect(page).toHaveURL(/\/$/);
    expect(await stored(page)).toBeNull();
    expect(deletes(api)).toHaveLength(0);
    expect(api.households.has(family.id)).toBe(true);

    // The code still opens it.
    await page.getByRole("link", { name: "Resume with family code" }).click();
    await page.getByLabel("Family code").fill(family.code);
    await page.getByRole("button", { name: "Open my family" }).click();
    await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  });
});
