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
