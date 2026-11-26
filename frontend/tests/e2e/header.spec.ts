import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

const banner = (page: Page) => page.getByRole("banner");
const stored = (page: Page) => page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY);

async function signIn(page: Page, api: FakeApi) {
  const family = api.seedHousehold();
  await page.addInitScript(
    ([key, value]) => {
      // Only the first load, so a test that signs out stays signed out after the page changes.
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, value);
      }
    },
    [STORAGE_KEY, api.storedSession(family)],
  );
  return family;
}

// The project runs on a phone-sized screen; the buttons beside the page links only show from "lg" up.
const WIDE = { width: 1280, height: 800 };

test.describe("Header", () => {
  test("offers Sign in when nobody is signed in", async ({ page }) => {
    await page.setViewportSize(WIDE);
    await page.goto("/");
    await expect(banner(page).getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
    await expect(banner(page).getByRole("link", { name: "My family" })).toHaveCount(0);
    await expect(banner(page).getByRole("button", { name: "Sign out" })).toHaveCount(0);
  });

  test("when signed in shows My family and Sign out instead of Sign in", async ({ page, api }) => {
    await page.setViewportSize(WIDE);
    await signIn(page, api);
    await page.goto("/");

    await expect(banner(page).getByRole("link", { name: "My family" })).toHaveAttribute("href", "/dashboard");
    await expect(banner(page).getByRole("button", { name: "Sign out" })).toBeVisible();
    await expect(banner(page).getByRole("link", { name: "Sign in", exact: true })).toHaveCount(0);
  });

  test("Sign out ends the session, goes home and brings Sign in back", async ({ page, api }) => {
    await page.setViewportSize(WIDE);
    const family = await signIn(page, api);
    await page.goto("/schemes");

    await banner(page).getByRole("button", { name: "Sign out" }).click();

    await expect(page).toHaveURL(/\/$/);
    await expect(banner(page).getByRole("link", { name: "Sign in", exact: true })).toBeVisible();
    expect(await stored(page)).toBeNull();
    expect(api.sessions.has(family.token)).toBe(false);
  });

  test("on a phone the menu holds My family and Sign out", async ({ page, api }) => {
    await signIn(page, api);
    await page.setViewportSize({ width: 390, height: 800 });
    await page.goto("/");

    // A tap that lands before the page's scripts have run does nothing, because the button has no
    // handler yet. Tap again until the menu is open; never tap an open menu, which would close it.
    const menuButton = page.getByRole("button", { name: "Menu" });
    const menu = page.locator("#mobile-menu");
    await expect(async () => {
      if ((await menuButton.getAttribute("aria-expanded")) !== "true") await menuButton.click();
      await expect(menu).toBeVisible({ timeout: 1000 });
    }).toPass({ timeout: 10_000 });
    await expect(menu.getByRole("link", { name: "My family" })).toBeVisible();
    await menu.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/$/);
    expect(await stored(page)).toBeNull();
  });
});
