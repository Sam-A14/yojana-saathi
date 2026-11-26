import { expect, test } from "./fixtures";

// --bg is #fbf8f1 in light and #0e1526 in dark (app/globals.css).
const LIGHT_BG = "rgb(251, 248, 241)";
const DARK_BG = "rgb(14, 21, 38)";
const THEME_KEY = "yojana.theme";

const pageColour = (page: import("@playwright/test").Page) =>
  page.evaluate(() => getComputedStyle(document.body).backgroundColor);
// On a phone the theme choice sits inside the Menu (A / A+ and the language stay in the top strip).
// From tablet width up it is in the strip, so there is no Menu button to press.
const openMenu = async (page: import("@playwright/test").Page) => {
  const menu = page.getByRole("button", { name: "Menu", exact: true });
  if (await menu.isVisible()) await menu.click();
};
const theme = (page: import("@playwright/test").Page) =>
  page.evaluate(() => document.documentElement.dataset.theme);

test.describe("on a phone that is set to dark", () => {
  test.use({ colorScheme: "dark" });

  test("the app is still light until the person chooses otherwise", async ({ page }) => {
    await page.goto("/signin");
    await openMenu(page);

    expect(await theme(page)).toBe("light");
    expect(await pageColour(page)).toBe(LIGHT_BG);
    await expect(page.getByRole("button", { name: "Light" })).toHaveAttribute("aria-pressed", "true");
  });

  test("'Dark' turns it dark and is remembered after a reload", async ({ page }) => {
    await page.goto("/signin");
    await openMenu(page);
    await page.getByRole("group", { name: "Colour theme" }).getByRole("button", { name: "Dark" }).click();

    expect(await pageColour(page)).toBe(DARK_BG);
    expect(await page.evaluate((k) => localStorage.getItem(k), THEME_KEY)).toBe("dark");

    await page.reload();
    expect(await theme(page)).toBe("dark");
    expect(await pageColour(page)).toBe(DARK_BG);
    await openMenu(page);
    await expect(page.getByRole("button", { name: "Dark" })).toHaveAttribute("aria-pressed", "true");
  });

  test("'Match device' follows the phone", async ({ page }) => {
    await page.goto("/signin");
    await openMenu(page);
    await page.getByRole("button", { name: "Match device" }).click();
    expect(await pageColour(page)).toBe(DARK_BG); // the phone is dark

    await page.emulateMedia({ colorScheme: "light" }); // the person changes the phone's setting
    expect(await pageColour(page)).toBe(LIGHT_BG);
    await page.emulateMedia({ colorScheme: "dark" });
    expect(await pageColour(page)).toBe(DARK_BG);
  });
});

test("a saved 'Match device' on a light phone stays light, and 'Light' beats a dark phone", async ({ page }) => {
  await page.addInitScript((k) => localStorage.setItem(k, "device"), THEME_KEY);
  await page.goto("/signin");
  expect(await theme(page)).toBe("device");
  expect(await pageColour(page)).toBe(LIGHT_BG);

  await page.emulateMedia({ colorScheme: "dark" });
  await openMenu(page);
  await page.getByRole("button", { name: "Light" }).click();
  expect(await pageColour(page)).toBe(LIGHT_BG);
});

test("a value we do not know falls back to light", async ({ page }) => {
  await page.addInitScript((k) => localStorage.setItem(k, "purple"), THEME_KEY);
  await page.goto("/signin");
  expect(await theme(page)).toBe("light");
});

test("with storage blocked the page is light and the toggle still works for this visit", async ({ page }) => {
  await page.addInitScript(() => {
    const blocked = () => {
      throw new Error("storage blocked");
    };
    Object.defineProperty(window, "localStorage", { get: blocked });
  });
  await page.goto("/signin");
  expect(await theme(page)).toBe("light");

  await openMenu(page);
  await page.getByRole("button", { name: "Dark" }).click();
  expect(await pageColour(page)).toBe(DARK_BG); // changes now, only is not remembered
});

test("the toggle is on the home page too, and its buttons are big enough to tap", async ({ page }) => {
  await page.goto("/");
  await openMenu(page);
  for (const name of ["Light", "Dark", "Match device"]) {
    const box = await page.getByRole("button", { name }).boundingBox();
    expect(box!.height, `${name} is at least 48px tall`).toBeGreaterThanOrEqual(48);
  }
});
