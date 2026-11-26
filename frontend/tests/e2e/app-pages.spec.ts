import { type Page } from "@playwright/test";
import { API } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// PR 2 of the portal redesign: the same look on every page except the home page (decision 026).

const scheme = (over: Record<string, unknown>) => ({
  slug: "s", name_en: "A scheme", name_hi: null, level: "central", state: null, category: "farmer",
  official_url: "https://example.gov.in/", benefit_text_en: null, benefit_text_hi: null,
  deadline_start: null, deadline_end: null, verified: false, verified_at: null, ...over,
});

async function schemesAre(page: Page, list: unknown[]) {
  await page.route(`${API}/schemes`, (route) =>
    route.fulfill({
      status: 200,
      headers: { "access-control-allow-origin": "*" },
      contentType: "application/json",
      body: JSON.stringify(list),
    }),
  );
}

test("every app page has the same title style and the soft band behind it", async ({ page, api }) => {
  void api;
  for (const path of ["/schemes", "/privacy", "/example", "/signin"]) {
    await page.goto(path);
    await expect(page.locator("h1.page-title"), path).toHaveCount(1);
    // The gold bar under the title is a fill, never gold text (it has no characters).
    const bar = await page.locator("h1.page-title").evaluate((h) => {
      const after = getComputedStyle(h, "::after");
      return { content: after.content, height: parseFloat(after.height) };
    });
    expect(bar.content, path).not.toBe("none");
    expect(bar.height, path).toBeGreaterThan(4);
  }
});

test("on a computer the scheme list is two to a row, on a phone one", async ({ page, api }) => {
  void api;
  await schemesAre(page, [scheme({ slug: "a", name_en: "First farm scheme" }), scheme({ slug: "b", name_en: "Second farm scheme" })]);
  const tops = async () => {
    const first = await page.getByRole("listitem").filter({ hasText: "First farm scheme" }).first().boundingBox();
    const second = await page.getByRole("listitem").filter({ hasText: "Second farm scheme" }).first().boundingBox();
    return [first!, second!] as const;
  };

  await page.goto("/schemes"); // the phone project's own size
  let [first, second] = await tops();
  expect(second.y).toBeGreaterThan(first.y + first.height - 1);

  await page.setViewportSize({ width: 1280, height: 900 });
  [first, second] = await tops();
  expect(second.y).toBeCloseTo(first.y, 0);
  expect(second.x).toBeGreaterThan(first.x + first.width - 1);
});

test("the form pages stay in a narrow column even on a wide screen", async ({ page, api }) => {
  void api;
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/signin");
  const box = await page.getByLabel("Your email address").boundingBox();
  expect(box!.width).toBeLessThan(700);
});

test("the dashboard does not show 'My data' under the placeholder while results load", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Kamla"]);
  api.eligibilityDelay = 1500;
  await page.addInitScript(([key, value]) => localStorage.setItem(key, value), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/dashboard");

  await expect(page.getByRole("status")).toBeVisible(); // the grey placeholder
  await expect(page.locator('section[aria-labelledby="my-data"]')).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "May qualify" }).first()).toBeVisible();
  await expect(page.locator('section[aria-labelledby="my-data"]')).toHaveCount(1);
});

test("an English page does not download the Hindi web font; a Hindi page does", async ({ page, api }) => {
  void api;
  const devanagariLoaded = () =>
    page.evaluate(() => [...document.fonts].some((f) => f.status === "loaded" && /devanagari/i.test(f.family)));

  await page.goto("/schemes");
  await expect(page.getByRole("button", { name: "हिन्दी" })).toBeVisible();
  expect(await devanagariLoaded()).toBe(false);

  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expect.poll(devanagariLoaded).toBe(true);
});
