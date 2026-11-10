import { expect, test, STORAGE_KEY } from "./fixtures";

test("home page shows the disclaimer and both ways in", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Start" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Resume with family code" })).toBeVisible();
  await expect(
    page.getByText(
      "Guidance only, not an official decision. Not a government app. We never ask for Aadhaar numbers.",
    ),
  ).toBeVisible();
});

test("a saved family code opens the family", async ({ page, api }) => {
  const family = api.seedHousehold();
  await page.goto("/");
  await page.getByRole("link", { name: "Resume with family code" }).click();

  await page.getByLabel("Family code").fill(`  ${family.code}\n`);
  await page.getByRole("button", { name: "Open my family" }).click();

  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  const stored = JSON.parse((await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY))!);
  expect(stored.code).toBe(family.code);
  // Every call about the household carried the token as a Bearer header.
  const calls = api.requests.filter((r) => r.path.startsWith("/households/"));
  expect(calls.length).toBeGreaterThan(0);
  for (const call of calls) expect(call.authorization).toBe(`Bearer ${family.token}`);
});

test("the whole downloaded file can be pasted", async ({ page, api }) => {
  const family = api.seedHousehold();
  await page.goto("/resume");

  await page.getByLabel("Family code").fill(`Yojana Saathi family code\n\n${family.code}\n\nKeep this file safe.\n`);
  await page.getByRole("button", { name: "Open my family" }).click();

  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
});

test("a text that is not a code, and a code that does not open anything, say so plainly", async ({ page, api }) => {
  const family = api.seedHousehold();
  await page.goto("/resume");

  await page.getByLabel("Family code").fill("hello");
  await page.getByRole("button", { name: "Open my family" }).click();
  await expect(page.getByText("This does not look like a family code.")).toBeVisible();

  const wrongToken = `${family.id}.${"A".repeat(43)}`;
  await page.getByLabel("Family code").fill(wrongToken);
  await page.getByRole("button", { name: "Open my family" }).click();
  await expect(page.getByText("This family code did not work.")).toBeVisible();
  expect(await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY)).toBeNull();
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
