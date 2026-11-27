import { type Page } from "@playwright/test";
import { type FakeApi, MISSING_HOME } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// The BPL question: three answers, and "Not sure" is never saved as "no".

const QUESTION = "Is your family on the BPL (Below Poverty Line) list?";
const group = (page: Page) => page.getByRole("group", { name: QUESTION });

async function signIn(page: Page, api: FakeApi, person: { token: string; email: string; id?: string | null }) {
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [STORAGE_KEY, api.storedSession(person)],
  );
}

async function openBasics(page: Page, api: FakeApi) {
  await signIn(page, api, api.seedSession());
  await page.goto("/setup/basics");
  await expect(group(page)).toBeVisible();
}

const created = (api: FakeApi) => api.requests.find((r) => r.method === "POST" && r.path === "/households")!.body;

// --- the three answers on the setup screen -----------------------------------------------------

test("the question has the owner's wording, the hint, and three labelled answers", async ({ page, api }) => {
  await openBasics(page, api);

  await expect(page.getByText("A BPL ration card is one sign.")).toBeVisible();
  for (const label of ["Yes", "No", "Not sure"]) {
    await expect(group(page).getByRole("radio", { name: label, exact: true })).toBeAttached();
  }
  await expect(group(page).getByRole("radio")).toHaveCount(3);
});

for (const [choice, expected] of [
  ["Yes", true],
  ["No", false],
  ["Not sure", null],
] as const) {
  test(`choosing "${choice}" saves ${expected === null ? "null (unknown)" : expected}`, async ({ page, api }) => {
    await openBasics(page, api);

    await group(page).getByLabel(choice, { exact: true }).check();
    await page.getByRole("button", { name: "Continue" }).click();

    await expect(page).toHaveURL(/\/setup\/members$/);
    expect(created(api)).toMatchObject({ is_bpl: expected });
    expect([...api.households.values()][0].fields).toMatchObject({ is_bpl: expected });
  });
}

test("a family that never touches the question is saved as unknown, not as 'no'", async ({ page, api }) => {
  await openBasics(page, api);
  await expect(group(page).getByLabel("Not sure", { exact: true })).toBeChecked(); // the starting point

  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/\/setup\/members$/);
  expect(created(api)).toMatchObject({ is_bpl: null });
  expect(created(api)).not.toMatchObject({ is_bpl: false });
});

test("changing your mind back to 'Not sure' sends null, never false", async ({ page, api }) => {
  await openBasics(page, api);
  await group(page).getByLabel("Yes", { exact: true }).check();
  await group(page).getByLabel("Not sure", { exact: true }).check();

  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/\/setup\/members$/);
  expect(created(api)).toMatchObject({ is_bpl: null });
});

// --- elder-friendly size -----------------------------------------------------------------------

test("every answer is a big target with 18px or larger text, and the hint is as large", async ({ page, api }) => {
  await openBasics(page, api);

  for (const label of ["Yes", "No", "Not sure"]) {
    const box = group(page).getByText(label, { exact: true });
    expect((await box.boundingBox())!.height, `${label} tap height`).toBeGreaterThanOrEqual(48);
    expect((await box.boundingBox())!.width, `${label} tap width`).toBeGreaterThanOrEqual(48);
    const size = await box.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(size, `${label} text size`).toBeGreaterThanOrEqual(18);
  }
  const hint = page.getByText("A BPL ration card is one sign.");
  expect(await hint.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(18);
  const legend = await group(page).locator("legend").evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(legend).toBeGreaterThanOrEqual(18);
});

test("the question is shown in Hindi with the owner's phrase", async ({ page, api }) => {
  await openBasics(page, api);
  await page.getByRole("button", { name: "हिन्दी" }).click();

  await expect(page.getByRole("group", { name: /गरीबी रेखा से नीचे \(BPL\)/ })).toBeVisible();
  await expect(page.getByText("BPL राशन कार्ड इसका एक संकेत है।")).toBeVisible();
});

// --- editing later ---------------------------------------------------------------------------------

async function openEdit(page: Page, api: FakeApi, is_bpl: boolean | null) {
  const family = api.seedHousehold({ state: "UP", is_bpl });
  api.seedMembers(family.id, ["Asha"]);
  await signIn(page, api, family);
  await page.goto("/household/edit");
  await expect(group(page)).toBeVisible();
  return family;
}

for (const [saved, label] of [
  [true, "Yes"],
  [false, "No"],
  [null, "Not sure"],
] as const) {
  test(`the edit screen shows a saved ${saved === null ? "unknown" : saved} as "${label}"`, async ({ page, api }) => {
    await openEdit(page, api, saved);

    await expect(group(page).getByLabel(label, { exact: true })).toBeChecked();
  });
}

test("on the edit screen, moving from No to Not sure clears the answer instead of keeping 'no'", async ({ page, api }) => {
  const family = await openEdit(page, api, false);

  await group(page).getByLabel("Not sure", { exact: true }).check();
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  const patch = api.requests.find((r) => r.method === "PATCH")!;
  expect(patch.body).toMatchObject({ is_bpl: null });
  expect(api.households.get(family.id)!.fields).toMatchObject({ is_bpl: null });
});

// --- a result that needs the answer ------------------------------------------------------------------

test("a result waiting for the BPL answer says so and links to the household screen", async ({ page, api }) => {
  // The sample family's "unknown" scheme, with one more rule that needs is_bpl.
  const fixture = structuredClone(MISSING_HOME) as unknown as typeof MISSING_HOME;
  for (const member of fixture.members) {
    for (const entry of (member as unknown as { schemes: { scheme: { slug: string }; unknown_rules: unknown[] }[] }).schemes) {
      if (entry.scheme.slug === "example-local-scheme") {
        entry.unknown_rules = [
          { rule: { field: "is_bpl", op: "is_true" }, fields: ["is_bpl"], matched_members: [], fixable: false, reasons: [] },
        ];
      }
    }
  }
  api.fixture = fixture;
  const family = api.seedHousehold({ state: "UP", is_bpl: null });
  api.seedMembers(family.id, ["Asha"]);
  await signIn(page, api, family);
  await page.goto("/dashboard");

  const item = page.getByRole("region", { name: "Asha", exact: true }).getByRole("listitem").filter({ hasText: "Example Local Scheme" });
  const row = item.getByRole("listitem").filter({ hasText: "We need to know if your family is BPL" });
  await expect(row).toBeVisible();
  await expect(row.getByRole("link", { name: "Answer this" })).toHaveAttribute("href", "/household/edit");

  await row.getByRole("link", { name: "Answer this" }).click();
  await expect(page).toHaveURL(/\/household\/edit$/);
  await expect(group(page)).toBeVisible();
});
