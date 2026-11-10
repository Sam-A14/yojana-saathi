import { expect, test } from "./fixtures";

test("home page shows the disclaimer and the ways in", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Start" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in with email" })).toBeVisible();
  await expect(page.getByRole("link", { name: "See an example" })).toBeVisible();
  await expect(
    page.getByText(
      "Guidance only, not an official decision. Not a government app. We never ask for Aadhaar numbers.",
    ),
  ).toBeVisible();
});

test("the language can be switched to Hindi and stays after a reload", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(
    page.getByRole("heading", { name: "देखें कि आपके परिवार को कौन-से सरकारी लाभ छूट रहे हैं" }),
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expect(page.getByText("हम आधार नंबर कभी नहीं माँगते।")).toBeVisible();

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");

  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByRole("link", { name: "Start" })).toBeVisible();
});

test("home page lists the schemes we check, with the unverified label", async ({ page, api }) => {
  await page.goto("/");

  const schemes = page.getByRole("region", { name: "Schemes we check" });
  await expect(schemes.getByRole("heading", { name: /Widow Pension/ })).toBeVisible();
  await expect(schemes.getByText("Not yet verified").first()).toBeVisible();
  await expect(schemes.getByRole("link", { name: "Official website" }).first()).toBeVisible();
  // The catalogue is public: no family token is sent with it.
  const call = api.requests.find((r) => r.path === "/schemes");
  expect(call?.authorization).toBeNull();
});

test("the A+ button makes text bigger and the choice is remembered", async ({ page }) => {
  await page.goto("/");
  // poll: the stylesheet can still be applying when the page reports it has loaded
  const size = () => page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
  await expect.poll(size).toBe(18);

  await page.getByRole("button", { name: /A\+/ }).click();
  await expect.poll(size).toBeGreaterThan(18);

  await page.reload();
  await expect.poll(size).toBeGreaterThan(18);
  await expect(page.getByRole("button", { name: /A\+/ })).toHaveAttribute("aria-pressed", "true");
});

test("the FAQ opens and shows the answer", async ({ page }) => {
  await page.goto("/");
  await page.getByText("Do I need to give my Aadhaar number?").click();
  await expect(page.getByText("We never ask for the number.")).toBeVisible();
});
