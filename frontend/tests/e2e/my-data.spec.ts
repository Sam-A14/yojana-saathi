import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

async function openDashboard(page: Page, api: FakeApi) {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(
    ([key, value]) => {
      // Runs on every page load, so only set it the first time: a test that clears it must stay cleared.
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, value);
      }
    },
    [STORAGE_KEY, api.storedSession(family)],
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

  test("says the email is erased too", async ({ page, api }) => {
    await openDashboard(page, api);

    await page.getByRole("button", { name: "Delete my data" }).click();

    await expect(page.getByRole("alertdialog", { name: "Delete everything?" })).toContainText("your email address");
  });

  test("deletes the user, their email and family on the server, then forgets this phone", async ({ page, api }) => {
    const family = await openDashboard(page, api);

    await page.getByRole("button", { name: "Delete my data" }).click();
    await page.getByRole("button", { name: "Yes, delete my data" }).click();

    await expect(page).toHaveURL(/\/deleted$/);
    await expect(page.getByRole("heading", { name: "Your data was deleted" })).toBeVisible();
    expect(deletes(api)).toEqual([
      expect.objectContaining({ path: "/me", authorization: `Bearer ${family.token}` }),
    ]);
    expect(api.households.has(family.id)).toBe(false);
    expect(api.users.has(family.email)).toBe(false);
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

test.describe("Sign out", () => {
  test("shows who is signed in, asks first, and staying signed in changes nothing", async ({ page, api }) => {
    const family = await openDashboard(page, api);
    await expect(page.getByText(`Signed in as ${family.email}`)).toBeVisible();

    await page.getByRole("button", { name: "Sign out" }).click();
    const dialog = page.getByRole("alertdialog", { name: "Sign out on this phone?" });
    await expect(dialog).toContainText("Your family’s information stays on our server.");
    await page.getByRole("button", { name: "No, stay signed in" }).click();

    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    expect(await stored(page)).not.toBeNull();
    expect(api.requests.some((r) => r.path === "/auth/sign-out")).toBe(false);
  });

  test("ends the session on the server and on this phone; the family stays and opens again by signing in", async ({ page, api }) => {
    const family = await openDashboard(page, api);

    await page.getByRole("button", { name: "Sign out" }).click();
    await page.getByRole("button", { name: "Yes, sign out" }).click();

    await expect(page).toHaveURL(/\/$/);
    expect(await stored(page)).toBeNull();
    expect(deletes(api)).toHaveLength(0);
    expect(api.households.has(family.id)).toBe(true);
    expect(api.sessions.has(family.token)).toBe(false); // the token is dead on the server too

    // The same email opens it again.
    await page.getByRole("link", { name: "Sign in with email" }).click();
    await page.getByLabel("Your email address").fill(family.email);
    await page.getByRole("button", { name: "Send me a code" }).click();
    await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
    await page.getByLabel("6-digit code").fill(api.lastCode(family.email));
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  });

  test("signs out on this phone even if the server cannot be reached", async ({ page, api }) => {
    await openDashboard(page, api);
    await page.getByRole("button", { name: "Sign out" }).click();

    api.offline = true;
    await page.getByRole("button", { name: "Yes, sign out" }).click();

    await expect(page).toHaveURL(/\/$/);
    expect(await stored(page)).toBeNull();
  });
});
