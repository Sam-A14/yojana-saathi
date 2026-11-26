import { expect, test } from "./fixtures";

// --bg is #fff8ec in light and #1a1410 in dark (app/globals.css).
const LIGHT_BG = "rgb(255, 248, 236)";
const DARK_BG = "rgb(26, 20, 16)";
const THEME_KEY = "yojana.theme";

const pageColour = (page: import("@playwright/test").Page) =>
  page.evaluate(() => getComputedStyle(document.body).backgroundColor);
const theme = (page: import("@playwright/test").Page) =>
  page.evaluate(() => document.documentElement.dataset.theme);

test.describe("on a phone that is set to dark", () => {
  test.use({ colorScheme: "dark" });

  test("the app is still light until the person chooses otherwise", async ({ page }) => {
    await page.goto("/signin");

    expect(await theme(page)).toBe("light");
    expect(await pageColour(page)).toBe(LIGHT_BG);
    await expect(page.getByRole("button", { name: "Light" })).toHaveAttribute("aria-pressed", "true");
  });

  test("'Dark' turns it dark and is remembered after a reload", async ({ page }) => {
    await page.goto("/signin");
    await page.getByRole("group", { name: "Colour theme" }).getByRole("button", { name: "Dark" }).click();

    expect(await pageColour(page)).toBe(DARK_BG);
    expect(await page.evaluate((k) => localStorage.getItem(k), THEME_KEY)).toBe("dark");

    await page.reload();
    expect(await theme(page)).toBe("dark");
    expect(await pageColour(page)).toBe(DARK_BG);
    await expect(page.getByRole("button", { name: "Dark" })).toHaveAttribute("aria-pressed", "true");
  });

  test("'Match device' follows the phone", async ({ page }) => {
    await page.goto("/signin");
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

  await page.getByRole("button", { name: "Dark" }).click();
  expect(await pageColour(page)).toBe(DARK_BG); // changes now, only is not remembered
});

test("the toggle is on the dark home page too, and its buttons are big enough to tap", async ({ page }) => {
  await page.goto("/");
  for (const name of ["Light", "Dark", "Match device"]) {
    const box = await page.getByRole("button", { name }).boundingBox();
    expect(box!.height, `${name} is at least 48px tall`).toBeGreaterThanOrEqual(48);
  }
});
