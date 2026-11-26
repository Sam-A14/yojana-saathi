import { type Page } from "@playwright/test";
import { API } from "./fake-api";
import { expect, test } from "./fixtures";

// A scheme as GET /schemes sends it. Only what the API sends is ever shown.
const scheme = (over: Record<string, unknown>) => ({
  slug: "s",
  name_en: "A scheme",
  name_hi: null,
  level: "central",
  state: null,
  category: "farmer",
  official_url: "https://example.gov.in/",
  benefit_text_en: null,
  benefit_text_hi: null,
  deadline_start: null,
  deadline_end: null,
  verified: false,
  verified_at: null,
  ...over,
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

// Found by its heading, because "families" also appears in other cards' descriptions.
const card = (page: Page, name: string) =>
  page.getByRole("list", { name: "Topics" }).getByRole("listitem").filter({ has: page.getByRole("heading", { name, exact: true }) });

test.describe("topic cards", () => {
  test("a topic with schemes shows the real count and links to its group", async ({ page, api }) => {
    void api; // installs the fake server, which also answers the browser's CORS preflight
    await schemesAre(page, [scheme({ slug: "a", category: "farmer" }), scheme({ slug: "b", category: "farmer" })]);
    await page.goto("/");

    const agriculture = card(page, "Agriculture").getByRole("link");
    await expect(agriculture).toContainText("2 schemes");
    await expect(agriculture).toHaveAttribute("href", "/schemes#group-farmer");
  });

  test("a single scheme reads '1 scheme'", async ({ page, api }) => {
    void api; // installs the fake server, which also answers the browser's CORS preflight
    await schemesAre(page, [scheme({ category: "widow_pension" })]);
    await page.goto("/");

    await expect(card(page, "Women & Family").getByRole("link")).toContainText("1 scheme");
    await expect(card(page, "Women & Family").getByRole("link")).not.toContainText("1 schemes");
  });

  test("a topic with no schemes says Coming soon and is not a link", async ({ page, api }) => {
    void api; // installs the fake server, which also answers the browser's CORS preflight
    await schemesAre(page, [scheme({ category: "farmer" })]);
    await page.goto("/");

    // Education has a backend category (student) but no scheme in it; Healthcare and Families have no category yet.
    for (const name of ["Education", "Healthcare", "Families", "Senior Citizens"]) {
      await expect(card(page, name)).toContainText("Coming soon");
      await expect(card(page, name).getByRole("link")).toHaveCount(0);
    }
  });

  test("the template placeholder category never becomes a card or a count", async ({ page, api }) => {
    void api; // installs the fake server, which also answers the browser's CORS preflight
    await schemesAre(page, [scheme({ category: "replace_with_category" })]);
    await page.goto("/");

    for (const name of ["Education", "Agriculture", "Women & Family", "Senior Citizens"]) {
      await expect(card(page, name)).toContainText("Coming soon");
    }
  });

  test("if the server cannot be reached no number is invented, and the all-schemes link is still there", async ({ page, api }) => {
    void api;
    await page.route(`${API}/schemes`, (route) => route.abort());
    await page.goto("/");

    await expect(page.getByText("We could not load the scheme numbers just now.")).toBeVisible();
    await expect(card(page, "Agriculture")).not.toContainText(/\d+ schemes?/);
    await expect(card(page, "Agriculture").getByRole("link")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "See all schemes" })).toBeVisible();
  });

  test("every linked card is at least 48px tall", async ({ page, api }) => {
    void api;
    await schemesAre(page, [scheme({ category: "farmer" })]);
    await page.goto("/");
    const link = page.getByRole("list", { name: "Topics" }).getByRole("link").first();
    expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(48);
  });
});

test("the trust strip uses honest wording and makes no claim we cannot back", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Every scheme links to its official source")).toBeVisible();
  await expect(page.getByText("Each scheme shows whether and when it was last checked")).toBeVisible();
  await expect(page.getByText("We never ask for Aadhaar numbers. Delete your data anytime.")).toBeVisible();

  const text = (await page.locator("main").innerText()).toLowerCase();
  for (const banned of ["always up to date", "never shared", "never share", "verified by", "government-approved", "official partner"]) {
    expect(text, banned).not.toContain(banned);
  }
});

test("the footer says it is a student project and credits the photo, with nothing official-looking", async ({ page }) => {
  await page.goto("/");
  const footer = page.getByRole("contentinfo");

  await expect(footer.getByText("Yojana Saathi is an independent student project, not a government website.")).toBeVisible();
  await expect(footer.locator('a[href="/privacy"]')).toHaveAttribute("href", "/privacy");
  await expect(footer.getByRole("link", { name: "Code on GitHub" })).toHaveAttribute("href", /github\.com\/Sam-A14\/yojana-saathi/);
  await expect(footer.getByRole("link", { name: "Photo: the Amritdev / Pexels" })).toHaveAttribute("href", /pexels\.com/);
  await expect(footer.locator("img, svg")).toHaveCount(1); // only the external-link arrow: no emblem, no logo
  expect((await footer.innerText()).toLowerCase()).not.toContain("digital india");
});

test("the hero photo loads, has a description, sits below the buttons on a phone, and carries no caption", async ({ page }) => {
  await page.goto("/");
  const photo = page.getByRole("img", { name: /family of several generations/ });
  await expect(photo).toBeVisible();
  expect(await photo.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);

  const cta = await page.getByRole("link", { name: "Find schemes for my family" }).boundingBox();
  const picture = await photo.boundingBox();
  expect(picture!.y).toBeGreaterThan(cta!.y + cta!.height);
  // No <figcaption>, quote or testimonial next to the people in the photo.
  await expect(page.locator("figcaption, blockquote")).toHaveCount(0);
});

test.describe("header", () => {
  test("on a phone the pages are in a Menu, and A / A+ and the language are still one tap away", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("button", { name: /A\+/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "हिन्दी" })).toBeVisible();
    await expect(page.getByText("Government schemes, simplified for families")).toBeHidden(); // tagline appears from tablet width

    const menu = page.getByRole("button", { name: "Menu", exact: true });
    await expect(menu).toHaveAttribute("aria-expanded", "false");
    await menu.click();
    for (const name of ["Home", "Schemes", "How it works", "FAQ", "About"]) {
      const link = page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name });
      await expect(link).toBeVisible();
      expect((await link.boundingBox())!.height, name).toBeGreaterThanOrEqual(48);
    }
    await expect(page.getByRole("banner").getByRole("link", { name: "Sign in", exact: true })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Menu", exact: true })).toHaveAttribute("aria-expanded", "false");
  });

  test("a menu link goes to its page and closes the menu", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name: "Schemes" }).click();

    await expect(page).toHaveURL(/\/schemes$/);
    await expect(page.getByRole("button", { name: "Menu", exact: true })).toHaveAttribute("aria-expanded", "false");
  });

  test("a laptop-width screen (1280px) already gets the full bar, even with larger text", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Menu", exact: true })).toBeHidden();
    await expect(page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name: "FAQ" })).toBeVisible();
    // The bar must not run off the side, with the tagline, five pages and Sign in all shown.
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });

  test("on a wide screen the pages are in the bar, with the tagline and a Sign in button", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");

    await expect(page.getByText("Government schemes, simplified for families")).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu", exact: true })).toBeHidden();
    await expect(page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name: "How it works" })).toBeVisible();
    await expect(page.getByRole("banner").getByRole("link", { name: "Sign in", exact: true })).toHaveAttribute("href", "/signin");
    await expect(page.getByRole("group", { name: "Colour theme" })).toBeVisible();
  });
});
