import { type Page } from "@playwright/test";
import { EMPTY_RESULTS, type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// After setup there was no way to add a person: the only place was step 2 of the setup. The
// dashboard now has "Add a family member" under the cards, and Edit / Remove on each card.

const IGNOAPS = "Indira Gandhi National Old Age Pension Scheme";
const card = (page: Page, name: string) => page.getByRole("region", { name, exact: true });
const calls = (api: FakeApi, method: string) => api.requests.filter((r) => r.method === method);

/** A finished UP household that is below the poverty line, with only its owner in it. */
async function openDashboard(page: Page, api: FakeApi, names = ["Asha"], fields: Record<string, unknown> = {}) {
  const family = api.seedHousehold({ state: "UP", area_type: "rural", income_band: "1_to_2_lakh", is_bpl: true, ...fields });
  api.seedMembers(family.id, names);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  return family;
}

async function addPerson(page: Page, name: string, relation: string, birthYear: string) {
  await page.getByRole("button", { name: "Add a family member" }).click();
  await page.getByLabel("Name or nickname").fill(name);
  await page.getByLabel("Who is this to you?").selectOption({ label: relation });
  await page.getByLabel("Year of birth").fill(birthYear);
  await page.getByRole("button", { name: "Save this person" }).click();
}

test.describe("adding a person from the dashboard", () => {
  test("a mother born in 1958, in a UP household below the poverty line, may qualify for IGNOAPS", async ({ page, api }) => {
    const family = await openDashboard(page, api);
    await expect(card(page, "Asha")).not.toContainText(IGNOAPS); // the owner alone: nothing for them here

    await addPerson(page, "Sita", "Mother", "1958");

    // What was sent: one new person, born 1958.
    const posts = calls(api, "POST").filter((r) => r.path.endsWith("/members"));
    expect(posts).toHaveLength(1);
    expect(posts[0].body).toMatchObject({ nickname: "Sita", relation: "mother", birth_year: 1958 });
    expect(api.households.get(family.id)!.members.map((m) => m.nickname)).toEqual(["Asha", "Sita"]);
    // What the person sees: back on the dashboard, a note, and the new card with the scheme.
    await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
    await expect(page.getByText("Sita was added. Their schemes are below.")).toBeVisible();
    const sita = card(page, "Sita");
    await expect(sita).toBeVisible();
    const scheme = sita.getByRole("listitem").filter({ hasText: IGNOAPS });
    await expect(scheme).toBeVisible();
    await expect(scheme).toContainText("May qualify");
    await expect(card(page, "Asha")).not.toContainText(IGNOAPS);
  });

  test("the same person in a family that is not below the poverty line gets no IGNOAPS", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha"], { is_bpl: false });
    await addPerson(page, "Sita", "Mother", "1958");

    await expect(card(page, "Sita")).toBeVisible();
    await expect(card(page, "Sita")).not.toContainText(IGNOAPS);
  });

  test("when nothing was found yet, 'Add a family member' is the main action", async ({ page, api }) => {
    api.fixture = EMPTY_RESULTS;
    await openDashboard(page, api);
    await expect(page.getByRole("heading", { name: "We did not find a scheme for your family yet" })).toBeVisible();

    await addPerson(page, "Sita", "Mother", "1958");

    await expect(card(page, "Sita").getByRole("listitem").filter({ hasText: IGNOAPS })).toBeVisible();
  });

  test("it can be done again, and a cancelled form changes nothing", async ({ page, api }) => {
    const family = await openDashboard(page, api);
    await page.getByRole("button", { name: "Add a family member" }).click();
    await page.getByLabel("Name or nickname").fill("Nobody");
    await page.getByRole("button", { name: "Cancel" }).click();
    expect(api.households.get(family.id)!.members).toHaveLength(1);

    await addPerson(page, "Sita", "Mother", "1958");
    await expect(card(page, "Sita")).toBeVisible();
    await addPerson(page, "Ravi", "Son", "1990");

    await expect(card(page, "Ravi")).toBeVisible();
    expect(api.households.get(family.id)!.members.map((m) => m.nickname)).toEqual(["Asha", "Sita", "Ravi"]);
    await expect(page.getByLabel("Name or nickname")).toHaveCount(0); // and no leftover form
  });

  test("a failed save keeps the form and what was typed", async ({ page, api }) => {
    await openDashboard(page, api);
    await page.getByRole("button", { name: "Add a family member" }).click();
    await page.getByLabel("Name or nickname").fill("Sita");
    await page.getByLabel("Who is this to you?").selectOption({ label: "Mother" });
    api.offline = true;
    await page.getByRole("button", { name: "Save this person" }).click();

    await expect(page.getByText(/could not reach the server/i)).toBeVisible();
    await expect(page.getByLabel("Name or nickname")).toHaveValue("Sita");
    await expect(page.getByRole("button", { name: "Save this person" })).toBeEnabled();
  });

  test("at 20 people the button is replaced by a plain sentence", async ({ page, api }) => {
    await openDashboard(page, api, Array.from({ length: 20 }, (_, i) => `P${i + 1}`));
    await expect(page.getByText("You have added the most people allowed (20).")).toBeVisible();
    await expect(page.getByRole("button", { name: "Add a family member" })).toHaveCount(0);
  });
});

test.describe("editing and removing a person", () => {
  test("Edit opens that person's form with their details, and saving changes them", async ({ page, api }) => {
    const family = await openDashboard(page, api, ["Asha", "Ramesh"]);

    await page.getByRole("button", { name: "Edit: Ramesh" }).click();
    await expect(page.getByRole("heading", { name: "Edit Ramesh" })).toBeVisible();
    await expect(page.getByLabel("Name or nickname")).toHaveValue("Ramesh");
    await page.getByLabel("Name or nickname").fill("Rameshwar");
    await page.getByLabel("Year of birth").fill("1980");
    await page.getByRole("button", { name: "Save this person" }).click();

    await expect(page.getByText("Rameshwar was updated.")).toBeVisible();
    await expect(card(page, "Rameshwar")).toBeVisible();
    expect(calls(api, "PATCH").filter((r) => r.path.includes("/members/"))).toHaveLength(1);
    expect(api.households.get(family.id)!.members.map((m) => [m.nickname, m.birth_year])).toEqual([["Asha", null], ["Rameshwar", 1980]]);
  });

  test("Remove asks first: 'No, keep' changes nothing, 'Yes, remove' removes the person", async ({ page, api }) => {
    const family = await openDashboard(page, api, ["Asha", "Ramesh"]);

    await page.getByRole("button", { name: "Remove: Ramesh" }).click();
    await expect(page.getByText("Remove Ramesh from your family?")).toBeVisible();
    await page.getByRole("button", { name: "No, keep" }).click();
    expect(calls(api, "DELETE")).toHaveLength(0);
    await expect(card(page, "Ramesh")).toBeVisible();

    await page.getByRole("button", { name: "Remove: Ramesh" }).click();
    await page.getByRole("button", { name: "Yes, remove" }).click();

    await expect(page.getByText("Ramesh was removed.")).toBeVisible();
    await expect(card(page, "Ramesh")).toHaveCount(0);
    expect(calls(api, "DELETE")).toHaveLength(1);
    expect(api.households.get(family.id)!.members.map((m) => m.nickname)).toEqual(["Asha"]);
  });

  test("the confirmation belongs to one person: asking about Ramesh does not ask about Asha", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha", "Ramesh"]);
    await page.getByRole("button", { name: "Remove: Ramesh" }).click();

    await expect(page.getByText("Remove Ramesh from your family?")).toBeVisible();
    await expect(page.getByText("Remove Asha from your family?")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Remove: Asha" })).toBeVisible();
  });
});

test.describe("for older readers", () => {
  test("Add, Edit and Remove are big (48px or more), with an icon and a word", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha", "Ramesh"]);

    for (const [name, word] of [
      ["Add a family member", "Add a family member"],
      ["Edit: Asha", "Edit"],
      ["Remove: Asha", "Remove"],
    ] as const) {
      const button = page.getByRole("button", { name });
      const box = (await button.boundingBox())!;
      expect(box.height, `${name} height`).toBeGreaterThanOrEqual(48);
      expect(box.width, `${name} width`).toBeGreaterThanOrEqual(48);
      await expect(button.locator("svg")).toHaveCount(1); // the icon
      await expect(button).toContainText(word); // and the word
      expect(await button.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(18);
    }
  });

  test("one main action: only 'Add a family member' is filled, with results or without", async ({ page, api }) => {
    const filled = (p: Page) => p.getByRole("main").locator("a.bg-primary, button.bg-primary");
    await openDashboard(page, api, ["Asha", "Ramesh"]);
    await expect(filled(page)).toHaveCount(1);
    await expect(filled(page)).toHaveText("Add a family member");
  });

  test("one main action in the empty state too", async ({ page, api }) => {
    api.fixture = EMPTY_RESULTS;
    await openDashboard(page, api);
    const filled = page.getByRole("main").locator("a.bg-primary, button.bg-primary");
    await expect(filled).toHaveCount(1);
    await expect(filled).toHaveText("Add a family member");
  });

  test("the new words are there in Hindi", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha"]);
    await page.getByRole("button", { name: "हिन्दी" }).click();

    await expect(page.getByRole("button", { name: "परिवार का सदस्य जोड़ें" })).toBeVisible();
    await expect(page.getByRole("button", { name: "बदलें: Asha" })).toBeVisible();
    await expect(page.getByRole("button", { name: "हटाएँ: Asha" })).toBeVisible();
  });
});

test("the example family has no Add, Edit or Remove: there is nobody to change", async ({ page, api }) => {
  void api;
  await page.goto("/example");
  await expect(page.getByRole("button", { name: "Add a family member" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Edit:|^Remove:/ })).toHaveCount(0);
});
