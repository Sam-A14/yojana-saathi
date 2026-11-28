import { type Page } from "@playwright/test";
import { expect, test, STORAGE_KEY } from "./fixtures";

// A scheme about the whole family (PMAY-Gramin: the house, the village, "no member pays income
// tax") gave the same answer on every person's card. It is now shown once, above the people.

const PMAY_G = "Pradhan Mantri Awaas Yojana - Gramin";
const WIDOW = "Indira Gandhi National Widow Pension Scheme (IGNWPS)";

async function openDashboard(
  page: Page,
  api: import("./fake-api").FakeApi,
  names: string[],
  relations: Record<string, string> = {},
) {
  const family = api.seedHousehold({
    state: "UP", district: "Lucknow", area_type: "rural", house_type: "kutcha", income_band: "1_to_2_lakh", category: "OBC",
  });
  api.seedMembers(family.id, names, relations);
  await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Your family’s schemes" })).toBeVisible();
  return family;
}

test.describe("schemes for the whole family", () => {
  test("PMAY-Gramin is shown once, in its own section, not on each person's card", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha", "Ravi", "Meena"]);

    const section = page.getByRole("region", { name: "For the whole family" });
    await expect(section).toBeVisible();
    await expect(section.getByRole("link", { name: PMAY_G })).toHaveCount(1);
    await expect(section).toContainText("May qualify");

    // Not on any card.
    for (const name of ["Asha", "Ravi", "Meena"]) {
      await expect(page.getByRole("region", { name, exact: true })).not.toContainText(PMAY_G);
    }
    // The whole page has it once.
    await expect(page.getByRole("link", { name: PMAY_G })).toHaveCount(1);
  });

  test("a scheme about a person stays on that person's card", async ({ page, api }) => {
    await openDashboard(page, api, ["Kamla", "Raju"]);

    await expect(page.getByRole("region", { name: "Kamla", exact: true })).toContainText(WIDOW);
    await expect(page.getByRole("region", { name: "For the whole family" })).not.toContainText(WIDOW);
  });

  test("its page says 'For your whole family' and opens for the family's main person", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha", "Ravi"], { Ravi: "self" });
    const main = api.households.values().next().value!.members[1]; // Ravi: relation "self"

    await page.getByRole("region", { name: "For the whole family" }).getByRole("link", { name: PMAY_G }).click();

    await expect(page).toHaveURL(new RegExp(`/scheme/pmay-g\\?member=${main.id}$`));
    const article = page.getByRole("article");
    await expect(article.getByText("For your whole family")).toBeVisible();
    await expect(article.getByRole("heading", { level: 1 })).toContainText("Pradhan Mantri Awaas Yojana");
    await expect(article.getByText("For Asha")).toHaveCount(0);
  });

  test("when the family changes so that the scheme no longer fits, the section goes away", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha"]);
    await expect(page.getByRole("region", { name: "For the whole family" })).toBeVisible();

    await page.getByRole("link", { name: "Edit household details" }).click();
    await page.getByRole("group", { name: "What kind of house does your family live in?" }).getByLabel("A pucca house (brick, cement)").check();
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await expect(page.getByRole("region", { name: "For the whole family" })).toHaveCount(0);
  });

  test("the words are in Hindi too", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha"]);
    await page.getByRole("button", { name: "हिन्दी" }).click();

    await expect(page.getByRole("region", { name: "पूरे परिवार के लिए" })).toBeVisible();
  });
});

test.describe("whose papers a whole-family scheme lists", () => {
  async function openScheme(page: Page, api: import("./fake-api").FakeApi) {
    const family = await openDashboard(page, api, ["Asha", "Ravi", "Meena"], { Ravi: "self" });
    const household = api.households.get(family.id)!;
    household.members[1].documents = { aadhaar_card: false }; // Ravi has no Aadhaar card
    household.members[2].documents = { aadhaar_card: false }; // nor Meena
    household.members[0].documents = { aadhaar_card: true };
    await page.goto("/dashboard");
    await page.getByRole("region", { name: "For the whole family" }).getByRole("link", { name: PMAY_G }).click();
    return { family, household, article: page.getByRole("article") };
  }

  test("starts with the family's main person and lets you pick another", async ({ page, api }) => {
    const { household, article } = await openScheme(page, api);
    const picker = article.getByLabel("Show papers for:");

    await expect(picker).toHaveValue(household.members[1].id); // Ravi, relation "self"
    await expect(article.getByText("Papers for Ravi:")).toBeVisible();
    await expect(article.getByText("Aadhaar card").first()).toBeVisible();

    await picker.selectOption({ label: "Asha" }); // Asha has her Aadhaar card
    await expect(page).toHaveURL(new RegExp(`member=${household.members[0].id}$`));
    await expect(article.getByText("Papers for Asha:")).toHaveCount(0);
    await expect(article.getByText("You have every paper this scheme asks for")).toBeVisible();

    await picker.selectOption({ label: "Meena" });
    await expect(article.getByText("Papers for Meena:")).toBeVisible();
  });

  test("the title stays 'For your whole family' whoever is picked", async ({ page, api }) => {
    const { article } = await openScheme(page, api);

    await article.getByLabel("Show papers for:").selectOption({ label: "Meena" });
    // Wait for the page to show Meena's papers first. Without this the check below passes at once,
    // before the page has changed, and proves nothing.
    await expect(article.getByText("Papers for Meena:")).toBeVisible();

    await expect(article.getByText("For your whole family")).toBeVisible();
    // Exact text: "Papers for Meena:" contains "for Meena" and is meant to be there. A title that
    // said "For Meena" would be the whole text of its element.
    await expect(article.getByText("For Meena", { exact: true })).toHaveCount(0);
  });

  test("a scheme about one person has no picker", async ({ page, api }) => {
    await openDashboard(page, api, ["Kamla", "Raju"]);
    await page.getByRole("region", { name: "Kamla", exact: true }).getByRole("link", { name: WIDOW }).first().click();

    await expect(page.getByRole("article").getByText("For Kamla")).toBeVisible();
    await expect(page.getByLabel("Show papers for:")).toHaveCount(0);
  });

  test("with a single person there is nothing to pick", async ({ page, api }) => {
    await openDashboard(page, api, ["Asha"], { Asha: "self" });
    await page.getByRole("region", { name: "For the whole family" }).getByRole("link", { name: PMAY_G }).click();

    await expect(page.getByRole("article").getByText("For your whole family")).toBeVisible();
    await expect(page.getByLabel("Show papers for:")).toHaveCount(0);
  });
});
