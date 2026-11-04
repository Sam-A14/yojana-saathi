import { type Page } from "@playwright/test";
import { expect, test, STORAGE_KEY } from "./fixtures";

const CODE_PATTERN = /[0-9a-f-]{36}\.[A-Za-z0-9_-]{43}/;

async function addPerson(page: Page, name: string, birthYear: number, relation?: string) {
  await page.getByLabel("Name or nickname").fill(name);
  if (relation) await page.getByLabel("Who is this to you?").selectOption({ label: relation });
  await page.getByLabel("Year of birth").fill(String(birthYear));
  await page.getByRole("button", { name: "Save this person" }).click();
}

test("a family goes from the home page to a finished setup", async ({ page, context, api }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const thisYear = new Date().getFullYear();

  // Home -> basics
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "See every government benefit your family may be missing" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Start" }).click();

  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  await page.getByLabel("District (optional)").fill("Lucknow");
  await page.getByLabel("Village (rural)").check();
  await page.getByLabel("Yearly income of the whole family").selectOption("1_to_2_lakh");
  await page.getByRole("button", { name: "Continue" }).click();

  // Family code: shown, copyable, downloadable, printable, and must be acknowledged.
  await expect(page.getByRole("heading", { name: "Your family code" })).toBeVisible();
  await expect(page.getByText("We cannot get this code back")).toBeVisible();
  const code = (await page.getByText(CODE_PATTERN).textContent())!.trim();
  expect(code).toMatch(CODE_PATTERN);

  await page.getByRole("button", { name: "Copy" }).click();
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(code);

  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download as text" }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toBe("yojana-saathi-family-code.txt");
  const file = await (await import("node:fs/promises")).readFile((await download.path())!, "utf8");
  expect(file).toContain(code);

  await page.evaluate(() => {
    (window as unknown as { printed: number }).printed = 0;
    window.print = () => ((window as unknown as { printed: number }).printed += 1);
  });
  await page.getByRole("button", { name: "Print" }).click();
  expect(await page.evaluate(() => (window as unknown as { printed: number }).printed)).toBe(1);

  // Saved on this device too.
  const stored = JSON.parse((await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY))!);
  expect(stored).toEqual({ code, step: "code" });

  const next = page.getByRole("button", { name: "Continue" });
  await expect(next).toBeDisabled();
  await page.getByLabel("I have saved my family code in a safe place").check();
  await next.click();

  // Members: the first form opens by itself, with "Myself" chosen.
  await expect(page.getByText("Step 3 of 5")).toBeVisible();
  await expect(page.getByLabel("Who is this to you?")).toHaveValue("self");
  await addPerson(page, "Asha", 1985);
  await page.getByRole("button", { name: "Add a person" }).click();
  await addPerson(page, "Ramesh", 1960, "Father");
  await page.getByRole("button", { name: "Add a person" }).click();
  await addPerson(page, "Gudiya", thisYear - 10, "Daughter");
  await expect(page.getByRole("listitem")).toHaveCount(3);
  await page.getByRole("button", { name: "Continue" }).click();

  // Documents: family papers once, then each person.
  await expect(page.getByText("Step 4 of 5")).toBeVisible();
  await page.getByRole("group", { name: "Ration card" }).getByLabel("Yes", { exact: true }).check();
  await page.getByRole("group", { name: "BPL (below poverty line) card" }).getByLabel("No", { exact: true }).check();
  await page.getByRole("group", { name: "Aadhaar card" }).first().getByLabel("Yes", { exact: true }).check();
  await page.getByRole("button", { name: "Save and continue" }).click();

  // Exclusion questions: adults only (Gudiya is 10).
  await expect(page.getByText("Step 5 of 5")).toBeVisible();
  await expect(page.getByRole("heading", { name: "For Asha" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "For Ramesh" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "For Gudiya" })).toHaveCount(0);
  const ramesh = page.getByRole("region", { name: "For Ramesh" });
  await ramesh.getByRole("group", { name: /income tax/ }).getByLabel("Yes", { exact: true }).check();
  await ramesh.getByRole("group", { name: /government pension/ }).getByLabel("Yes, less than ₹10,000 a month").check();
  await page.getByRole("button", { name: "Finish setup" }).click();

  // The dashboard: the setup answers lead straight to results, one card per person.
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  for (const name of ["Asha", "Ramesh", "Gudiya"]) {
    await expect(page.getByRole("region", { name, exact: true })).toBeVisible();
  }
  expect(JSON.parse((await page.evaluate((k) => localStorage.getItem(k), STORAGE_KEY))!).step).toBe("done");

  // What the API was told.
  const household = [...api.households.values()][0];
  expect(household.fields).toMatchObject({ state: "UP", district: "Lucknow", area_type: "rural", income_band: "1_to_2_lakh", category: null });
  const [asha, rameshRow, gudiya] = household.members;
  // A "no" for a family paper is written for everyone; "not sure" answers are left out.
  expect(asha.documents).toEqual({ ration_card: true, bpl_card: false, aadhaar_card: true });
  expect(rameshRow.documents).toEqual({ ration_card: true, bpl_card: false });
  expect(gudiya.documents).toEqual({ ration_card: true, bpl_card: false });
  expect(rameshRow).toMatchObject({ paid_income_tax_last_year: true, pension_band: "below_10k", govt_employee: null });
  expect(asha).toMatchObject({ paid_income_tax_last_year: null, holds_constitutional_post: null });
  // The child was never asked, so nothing was sent for her: only the two adults were updated.
  expect(gudiya.paid_income_tax_last_year).toBeNull();
  expect(api.requests.filter((r) => r.method === "PATCH")).toHaveLength(2);

  // Every call about the household carried the token, as a Bearer header.
  const token = code.split(".")[1];
  const protectedCalls = api.requests.filter((r) => r.path.startsWith("/households/"));
  expect(protectedCalls.length).toBeGreaterThan(5);
  for (const call of protectedCalls) expect(call.authorization).toBe(`Bearer ${token}`);
  // The token never appears in a URL.
  expect(api.requests.some((r) => r.path.includes(token))).toBe(false);
});

test("a person can be edited and removed, and needs a name", async ({ page, api }) => {
  void api;
  await page.goto("/setup/basics");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("I have saved my family code in a safe place").check();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText("Please enter a name or nickname.")).toBeVisible();

  await page.getByLabel("Name or nickname").fill("Asha");
  await page.getByLabel("Year of birth").fill("1850");
  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText(/Enter a year between 1900 and \d{4}/)).toBeVisible();

  await page.getByLabel("Year of birth").fill("1985");
  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText("Born 1985")).toBeVisible();

  await page.getByRole("button", { name: "Edit: Asha" }).click();
  await page.getByLabel("Name or nickname").fill("Asha Devi");
  await page.getByRole("button", { name: "Save this person" }).click();
  await expect(page.getByText("Asha Devi")).toBeVisible();

  await page.getByRole("button", { name: "Remove: Asha Devi" }).click();
  await page.getByRole("button", { name: "No, keep" }).click();
  await expect(page.getByText("Asha Devi")).toBeVisible();
  await page.getByRole("button", { name: "Remove: Asha Devi" }).click();
  await page.getByRole("button", { name: "Yes, remove" }).click();
  await expect(page.getByText("Asha Devi")).toHaveCount(0);

  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Add at least one person to continue.")).toBeVisible();
});

test("the family stops at 20 people", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, 20);
  await page.addInitScript(
    ([key, code]) => localStorage.setItem(key, JSON.stringify({ code, step: "members" })),
    [STORAGE_KEY, family.code],
  );

  await page.goto("/setup/members");

  await expect(page.getByRole("listitem")).toHaveCount(20);
  await expect(page.getByText("You have added the most people allowed (20).")).toBeVisible();
  await expect(page.getByRole("button", { name: "Add a person" })).toHaveCount(0);
});

test("starting again never silently replaces a saved family code", async ({ page, api }) => {
  const family = api.seedHousehold();
  await page.addInitScript(
    ([key, code]) => localStorage.setItem(key, JSON.stringify({ code, step: "documents" })),
    [STORAGE_KEY, family.code],
  );

  await page.goto("/setup/basics");
  await expect(page.getByText("You already started setting up a family on this phone.")).toBeVisible();
  await page.getByRole("button", { name: "Continue where I stopped" }).click();
  await expect(page).toHaveURL(/\/setup\/documents$/);

  await page.goto("/setup/basics");
  await page.getByRole("button", { name: "Start a new family" }).click();
  await expect(page.getByLabel("District (optional)")).toBeVisible();
});

test("a setup screen without a saved family goes back to the first step", async ({ page }) => {
  await page.goto("/setup/members");

  await expect(page).toHaveURL(/\/setup\/basics$/);
});
