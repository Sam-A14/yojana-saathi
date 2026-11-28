import { type Page } from "@playwright/test";
import { type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// "What are they studying now?" (current_study_level) is asked only of a student. It is separate
// from "Schooling finished": a child in Class 9 has finished Class 8, which that list cannot say.

const LEVEL = "What are they studying now?";

async function openAddForm(page: Page, api: FakeApi) {
  const family = api.seedHousehold({ state: "UP", area_type: "rural", income_band: "1_to_2_lakh", is_bpl: true });
  api.seedMembers(family.id, ["Asha"]);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Add a family member" }).click();
  await page.getByLabel("Name or nickname").fill("Ravi");
  await page.getByLabel("Who is this to you?").selectOption({ label: "Son" });
  return family;
}

const savedBody = (api: FakeApi) =>
  api.requests.filter((r) => r.method === "POST" && r.path.endsWith("/members")).at(-1)!.body;

test.describe("what the person is studying now", () => {
  test("is hidden until the answer to 'studying now' is Yes", async ({ page, api }) => {
    await openAddForm(page, api);
    await expect(page.getByLabel(LEVEL)).toHaveCount(0);

    const student = page.getByRole("group", { name: "Is this person studying now?" });
    await student.getByLabel("Yes").check();
    await expect(page.getByLabel(LEVEL)).toBeVisible();

    await student.getByLabel("No", { exact: true }).check();
    await expect(page.getByLabel(LEVEL)).toHaveCount(0);
  });

  test("a student's level is sent with the person", async ({ page, api }) => {
    await openAddForm(page, api);
    await page.getByRole("group", { name: "Is this person studying now?" }).getByLabel("Yes").check();
    await page.getByLabel(LEVEL).selectOption({ label: "Class 9 or 10" });
    await page.getByRole("button", { name: "Save this person" }).click();

    await expect.poll(() => api.requests.some((r) => r.method === "POST" && r.path.endsWith("/members"))).toBe(true);
    expect(savedBody(api)).toMatchObject({ is_student: true, current_study_level: "class_9_10" });
  });

  test("changing to 'not studying' clears the level, so no old answer stays behind", async ({ page, api }) => {
    await openAddForm(page, api);
    const student = page.getByRole("group", { name: "Is this person studying now?" });
    await student.getByLabel("Yes").check();
    await page.getByLabel(LEVEL).selectOption({ label: "Class 9 or 10" });
    await student.getByLabel("No", { exact: true }).check();
    await page.getByRole("button", { name: "Save this person" }).click();

    await expect.poll(() => api.requests.some((r) => r.method === "POST" && r.path.endsWith("/members"))).toBe(true);
    expect(savedBody(api)).toMatchObject({ is_student: false, current_study_level: null });
  });

  test("left as 'not sure', the level is sent as null (unknown), never a guess", async ({ page, api }) => {
    await openAddForm(page, api);
    await page.getByRole("group", { name: "Is this person studying now?" }).getByLabel("Yes").check();
    await page.getByRole("button", { name: "Save this person" }).click();

    await expect.poll(() => api.requests.some((r) => r.method === "POST" && r.path.endsWith("/members"))).toBe(true);
    expect(savedBody(api)).toMatchObject({ is_student: true, current_study_level: null });
  });
});
