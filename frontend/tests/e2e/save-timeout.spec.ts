import { type Page } from "@playwright/test";
import { API, type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// A save that never gets an answer used to leave "Saving…" on the screen forever. Now it gives up
// after 15 seconds, PATCH and PUT are tried once more, and POST is not. The browser clock is moved
// forward instead of waiting, so these take about a second each.

const MESSAGE = "Saving is taking too long. Your answers are still here. Try again.";

async function signedIn(page: Page, person: { token: string; email: string; id?: string | null }, api: FakeApi) {
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(person)]);
}

async function openEdit(page: Page, api: FakeApi) {
  const family = api.seedHousehold({ state: "UP", district: "Agra", area_type: "rural", income_band: "1_to_2_lakh", category: "OBC" });
  api.seedMembers(family.id, ["Asha"]);
  await page.clock.install();
  await signedIn(page, family, api);
  await page.goto("/household/edit");
  await expect(page.getByLabel("District (optional)")).toHaveValue("Agra");
  return family;
}

/** The nth request of this kind goes nowhere: no answer, no error, like a stalled connection. */
async function stall(page: Page, method: string, pathPattern: string, which: (attempt: number) => boolean) {
  const attempts = { count: 0 };
  await page.route(`${API}${pathPattern}`, async (route) => {
    if (route.request().method() !== method) return route.fallback();
    attempts.count++;
    if (which(attempts.count)) await new Promise(() => {}); // never answers
    else await route.fallback(); // the fake server answers normally
  });
  return attempts;
}

test.describe("saving the household details", () => {
  test("a stalled save is tried again by itself and goes through", async ({ page, api }) => {
    const family = await openEdit(page, api);
    const attempts = await stall(page, "PATCH", "/households/*", (n) => n === 1);

    await page.getByLabel("District (optional)").fill("Kanpur");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByRole("button", { name: "Saving…" })).toBeVisible();
    await page.clock.fastForward(15_000); // the first try is given up on

    await expect.poll(() => attempts.count).toBe(2); // and sent again
    await expect(page).toHaveURL(/\/dashboard$/); // the second try worked
    expect(api.households.get(family.id)!.fields).toMatchObject({ district: "Kanpur" });
    await expect(page.getByText(MESSAGE)).toHaveCount(0);
  });

  test("a save stalled twice says so, keeps the answers and can be tried again", async ({ page, api }) => {
    const family = await openEdit(page, api);
    const attempts = await stall(page, "PATCH", "/households/*", (n) => n <= 2);

    await page.getByLabel("District (optional)").fill("Kanpur");
    await page.getByRole("button", { name: "Save changes" }).click();
    await page.clock.fastForward(15_000);
    await expect.poll(() => attempts.count).toBe(2);
    await page.clock.fastForward(15_000);

    await expect(page.getByText(MESSAGE)).toBeVisible();
    await expect(page.getByRole("button", { name: "Save changes" })).toBeEnabled(); // the form is usable again
    await expect(page.getByLabel("District (optional)")).toHaveValue("Kanpur"); // nothing was lost
    expect(attempts.count).toBe(2); // exactly two tries, never a third
    await page.clock.fastForward(60_000);
    expect(attempts.count).toBe(2);
    expect(api.households.get(family.id)!.fields).toMatchObject({ district: "Agra" }); // nothing saved

    await page.getByRole("button", { name: "Save changes" }).click(); // "Try again": a fresh save
    await expect(page).toHaveURL(/\/dashboard$/);
    expect(api.households.get(family.id)!.fields).toMatchObject({ district: "Kanpur" });
  });

  test("the message is also there in Hindi", async ({ page, api }) => {
    await openEdit(page, api);
    await stall(page, "PATCH", "/households/*", () => true);
    await page.getByRole("button", { name: "हिन्दी" }).click();

    await page.getByRole("button", { name: /सहेजें|बदलाव/ }).click();
    await page.clock.fastForward(15_000);
    await page.clock.fastForward(15_000);

    await expect(page.getByText("सहेजने में बहुत समय लग रहा है। आपके जवाब यहीं हैं। फिर से कोशिश करें।")).toBeVisible();
  });

  test("a save that answers at 14 seconds is not repeated", async ({ page, api }) => {
    const family = await openEdit(page, api);
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    let attempts = 0;
    await page.route(`${API}/households/*`, async (route) => {
      if (route.request().method() !== "PATCH") return route.fallback();
      attempts++;
      await gate; // a slow answer that does arrive
      await route.fallback();
    });

    await page.getByLabel("District (optional)").fill("Kanpur");
    await page.getByRole("button", { name: "Save changes" }).click();
    await page.clock.fastForward(14_000);
    release();

    await expect(page).toHaveURL(/\/dashboard$/);
    expect(attempts).toBe(1);
    expect(api.households.get(family.id)!.fields).toMatchObject({ district: "Kanpur" });
  });

  test("a slow read is never given up on (a sleeping server needs its time)", async ({ page, api }) => {
    const family = api.seedHousehold({ state: "UP", district: "Agra" });
    api.seedMembers(family.id, ["Asha"]);
    await page.clock.install();
    await signedIn(page, family, api);
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    await page.route(`${API}/households/*`, async (route) => {
      if (route.request().method() !== "GET" || route.request().url().includes("/eligibility") || route.request().url().includes("/members")) return route.fallback();
      await gate;
      await route.fallback();
    });

    await page.goto("/household/edit");
    await page.clock.fastForward(40_000); // far past the 15 seconds a save is allowed
    await expect(page.getByText(MESSAGE)).toHaveCount(0);
    release();

    await expect(page.getByLabel("District (optional)")).toHaveValue("Agra");
  });
});

test.describe("adding things (POST) is never repeated", () => {
  test("a stalled first-step save says so after 15 seconds and sent only one request", async ({ page, api }) => {
    const person = api.seedSession();
    await page.clock.install();
    await signedIn(page, person, api);
    const attempts = await stall(page, "POST", "/households", () => true);
    await page.goto("/setup/basics");
    await page.getByLabel("District (optional)").fill("Lucknow");

    await page.getByRole("button", { name: "Continue" }).click();
    await page.clock.fastForward(15_000);

    await expect(page.getByText(MESSAGE)).toBeVisible();
    await page.clock.fastForward(60_000);
    expect(attempts.count).toBe(1); // never repeated: it might have arrived
    await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();
    await expect(page.getByLabel("District (optional)")).toHaveValue("Lucknow");
    expect([...api.households.values()]).toHaveLength(0);
  });
});
