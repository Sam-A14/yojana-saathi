import { expect, test, STORAGE_KEY } from "./fixtures";

test("'Try a demo family' shows a made-up family with no sign-in and no family data call", async ({ page, api }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Try a demo family" }).click();

  await expect(page).toHaveURL(/\/example$/);
  await expect(page.getByText("Demo, not a real family", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("This is a made-up family")).toBeVisible();
  await expect(page.getByRole("region", { name: "Asha", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Check my own family" })).toHaveAttribute("href", "/setup/basics");
  // Several schemes across several people's cards, and nothing on the page edits anything.
  expect(await page.getByRole("region").getByRole("link", { name: /scheme|yojana|pension|pm|scholarship/i }).count()).toBeGreaterThanOrEqual(4);
  await expect(page.getByRole("button", { name: /add|edit|delete|save/i })).toHaveCount(0);
  // Nothing about a household was asked of the server, and nobody had to sign in.
  expect(api.requests.filter((r) => r.path.startsWith("/households") || r.path === "/me")).toEqual([]);
  expect(await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY)).toBeNull();
});

test("an example scheme opens the real scheme page, still labelled Example", async ({ page, api }) => {
  await page.goto("/example");
  const card = page.getByRole("region", { name: "Kamla", exact: true });
  await card.getByRole("link", { name: /Widow Pension/ }).click();

  await expect(page).toHaveURL(/\/example\/scheme\/ignwps\?member=/);
  await expect(page.getByText("This is a made-up family").filter({ visible: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Widow Pension/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why this may fit" })).toBeVisible();
  expect(api.requests.some((r) => r.path.startsWith("/households"))).toBe(false);

  await page.getByRole("link", { name: "Back to your family’s schemes" }).click();
  await expect(page).toHaveURL(/\/example$/);
});

test("the example is in Hindi when the language is Hindi", async ({ page }) => {
  await page.goto("/example");
  await page.getByRole("button", { name: "हिन्दी" }).click();

  await expect(page.getByRole("heading", { name: "एक डेमो परिवार" })).toBeVisible();
});

test("the home page wakes the server in the background, without a banner", async ({ page, api }) => {
  await page.goto("/");

  await expect.poll(() => api.requests.some((r) => r.path === "/health")).toBe(true);
  await expect(page.getByText(/Waking up the server/)).toHaveCount(0);
});

test("a request that takes over 4 seconds shows the waking-up message, then removes it", async ({ page, api }) => {
  await page.goto("/signin");
  await page.getByLabel("Your email address").fill("asha@example.com");

  api.latency = 6500;
  const sent = Date.now();
  await page.getByRole("button", { name: "Send me a code" }).click();

  const banner = page.getByRole("status").filter({ hasText: "Waking up the server. This can take up to a minute the first time." });
  await expect(banner).toHaveCount(0); // not yet: nothing shows in the first seconds
  await expect(banner).toBeVisible({ timeout: 6000 });
  expect(Date.now() - sent).toBeGreaterThanOrEqual(3900); // and not before about 4 seconds
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible({ timeout: 8000 });
  await expect(banner).toHaveCount(0);
});

test("a request that takes 3.5 seconds is slow but shows no waking-up message", async ({ page, api }) => {
  await page.goto("/signin");
  await page.getByLabel("Your email address").fill("asha@example.com");

  api.latency = 3500;
  await page.getByRole("button", { name: "Send me a code" }).click();

  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible({ timeout: 6000 });
  await expect(page.getByText(/Waking up the server/)).toHaveCount(0);
});

test("a quick answer never shows the waking-up message", async ({ page, api }) => {
  await page.goto("/signin");
  await page.getByLabel("Your email address").fill("asha@example.com");

  api.latency = 300;
  await page.getByRole("button", { name: "Send me a code" }).click();

  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  await expect(page.getByText(/Waking up the server/)).toHaveCount(0);
});
