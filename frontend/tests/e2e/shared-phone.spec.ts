import { expect, test, STORAGE_KEY } from "./fixtures";

// Next.js keeps pages the person has left (hidden, with their state) so Back is instant. On a
// phone that several people share, that must never show one family what another typed or loaded.
// Every move below is a click (no page reload), because a reload would clear the state anyway.

test("the next family never sees the previous family's results, even while theirs load", async ({ page, api }) => {
  const first = api.seedHousehold();
  api.seedMembers(first.id, ["Kamla", "Asha"]);
  const second = api.seedHousehold();
  api.seedMembers(second.id, ["Meena"]);
  await page.addInitScript(
    ([key, code]) => {
      if (!sessionStorage.getItem("seeded")) {
        sessionStorage.setItem("seeded", "1");
        localStorage.setItem(key, JSON.stringify({ code, step: "done" }));
      }
    },
    [STORAGE_KEY, first.code],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("region", { name: "Kamla", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Forget this device" }).click();
  await page.getByRole("button", { name: "Yes, forget this phone" }).click();
  await expect(page).toHaveURL(/\/$/);

  // The second family signs in with a slow server: for a while only "loading" may show.
  api.eligibilityDelay = 1500;
  await page.getByRole("link", { name: "Resume with family code" }).click();
  await page.getByLabel("Family code").fill(second.code);
  await page.getByRole("button", { name: "Open my family" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Checking schemes for your family…")).toBeVisible();
  await expect(page.getByText("Kamla")).toHaveCount(0);
  await expect(page.getByText("Asha")).toHaveCount(0);

  await expect(page.getByRole("region", { name: "Meena", exact: true })).toBeVisible();
  await expect(page.getByText("Kamla")).toHaveCount(0);
});

test("a pasted family code is not left in the box for the next person", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Asha"]);
  await page.goto("/resume");
  await page.getByLabel("Family code").fill(family.code);
  await page.getByRole("button", { name: "Open my family" }).click();
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();

  await page.getByRole("button", { name: "Forget this device" }).click();
  await page.getByRole("button", { name: "Yes, forget this phone" }).click();
  await page.getByRole("link", { name: "Resume with family code" }).click();

  await expect(page.getByLabel("Family code")).toHaveValue("");
});

test("a new family's forms start empty and unticked", async ({ page, api }) => {
  void api;
  // Family one: the basics typed in, and "I have saved my code" ticked.
  await page.goto("/setup/basics");
  await page.getByLabel("District (optional)").fill("Lucknow");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("I have saved my family code in a safe place").check();

  // Back to the start by clicking, then begin again as a different family.
  await page.getByRole("link", { name: "Yojana Saathi" }).click();
  await page.getByRole("link", { name: "Start" }).click();
  await page.getByRole("button", { name: "Start a new family" }).click();
  await expect(page.getByLabel("District (optional)")).toHaveValue("");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByLabel("I have saved my family code in a safe place")).not.toBeChecked();
  await expect(page.getByRole("button", { name: "Continue" })).toBeDisabled();
});

test("results are asked for again after the family answers a question", async ({ page, api }) => {
  const family = api.seedHousehold();
  api.seedMembers(family.id, ["Kamla", "Asha"]);
  await page.addInitScript(
    ([key, code]) => localStorage.setItem(key, JSON.stringify({ code, step: "done" })),
    [STORAGE_KEY, family.code],
  );
  await page.goto("/dashboard");
  await expect(page.getByRole("region", { name: "Kamla", exact: true })).toBeVisible();
  const asked = () => api.requests.filter((r) => r.path.endsWith("/eligibility")).length;
  expect(asked()).toBe(1);

  // Answer a paper on the setup screen, go through to the end, and come back.
  await page.getByRole("region", { name: "Kamla", exact: true }).getByRole("link", { name: "Answer this" }).click();
  await page.getByRole("button", { name: "Save and continue" }).click();
  await page.getByRole("button", { name: "Finish setup" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect.poll(asked).toBeGreaterThanOrEqual(2);
});
