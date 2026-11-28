import { type Locator, type Page } from "@playwright/test";
import { API, EMPTY_RESULTS, type FakeApi } from "./fake-api";
import { expect, test, STORAGE_KEY } from "./fixtures";

// A way out to myScheme for families who want to look further than the schemes we check. A plain
// link that opens in a new tab: nothing is fetched from myScheme and no data is copied.

const LABEL = "See more schemes on myScheme (not checked by Yojana Saathi)";
const SEARCH = "https://www.myscheme.gov.in/search";

const scheme = (over: Record<string, unknown>) => ({
  slug: "s", name_en: "A scheme", name_hi: null, level: "central", state: null, category: "farmer",
  official_url: "https://example.gov.in/", benefit_text_en: null, benefit_text_hi: null,
  not_checked_en: [], not_checked_hi: null, deadline_start: null, deadline_end: null, verified: false, verified_at: null,
  ...over,
});

async function schemesAre(page: Page, list: unknown[]) {
  await page.route(`${API}/schemes`, (route) =>
    route.fulfill({ status: 200, headers: { "access-control-allow-origin": "*" }, contentType: "application/json", body: JSON.stringify(list) }),
  );
}

// Every request the page makes: none may go to myScheme.
function watchMyScheme(page: Page) {
  const seen: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("myscheme.gov.in")) seen.push(request.url());
  });
  return seen;
}

const links = (where: Page | Locator) => where.getByRole("link", { name: new RegExp(`^${LABEL.replace(/[()]/g, "\\$&")}`) });

test.describe("the myScheme link", () => {
  test("the dashboard's 'no scheme found' card has it, opening myScheme's search in a new tab", async ({ page, api }: { page: Page; api: FakeApi }) => {
    api.fixture = EMPTY_RESULTS;
    const family = api.seedHousehold({ state: "UP", area_type: "rural", income_band: "1_to_2_lakh", house_type: "pucca" });
    api.seedMembers(family.id, ["Asha"]);
    await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [STORAGE_KEY, api.storedSession(family)]);
    const touched = watchMyScheme(page);
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "We did not find a scheme for your family yet" })).toBeVisible();

    const link = links(page);
    await expect(link).toHaveCount(1);
    await expect(link).toHaveAttribute("href", SEARCH);
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", /noopener/);
    await expect(link).toContainText("(opens in a new tab)"); // for screen readers
    expect(touched).toEqual([]); // nothing was fetched from myScheme
  });

  test("each topic on the Schemes page has one, with its words; a state scheme adds Uttar Pradesh", async ({ page }) => {
    await schemesAre(page, [
      scheme({ slug: "kisan", category: "farmer", name_en: "A farm scheme" }),
      scheme({ slug: "vridha", category: "pension", level: "state", state: "UP", name_en: "A state pension" }),
      scheme({ slug: "mystery", category: "something-new", name_en: "A mystery scheme" }),
    ]);
    const touched = watchMyScheme(page);
    await page.goto("/schemes");
    await expect(page.getByRole("heading", { name: "A farm scheme" })).toBeVisible();

    const farmers = page.getByRole("region", { name: "Farmers" });
    await expect(links(farmers)).toHaveAttribute("href", `${SEARCH}?keyword=Farmer`);
    const pension = page.getByRole("region", { name: "Pensions" });
    await expect(links(pension)).toHaveAttribute("href", `${SEARCH}?keyword=Pension+Uttar+Pradesh`);
    // a topic we have no words for has none of its own, and the page ends with ONE link, not two:
    // the general link is shown only when no topic has its own
    await expect(links(page.getByRole("region", { name: "Other" }))).toHaveCount(0);
    await expect(links(page)).toHaveCount(2);
    await expect(page.locator(`a[href="${SEARCH}"]`)).toHaveCount(0);
    for (const link of await links(page).all()) await expect(link).toHaveAttribute("target", "_blank");
    expect(touched).toEqual([]);
  });

  test("a Schemes page where no topic has words ends with the one general link", async ({ page }) => {
    await schemesAre(page, [scheme({ slug: "mystery", category: "something-new", name_en: "A mystery scheme" })]);
    await page.goto("/schemes");
    await expect(page.getByRole("heading", { name: "A mystery scheme" })).toBeVisible();

    await expect(links(page)).toHaveCount(1);
    await expect(links(page)).toHaveAttribute("href", SEARCH);
  });

  test("the words are in Hindi too, and the address does not change with the language", async ({ page }) => {
    await schemesAre(page, [scheme({ slug: "kisan", category: "farmer", name_en: "A farm scheme" })]);
    await page.goto("/schemes");
    await page.getByRole("button", { name: "हिन्दी" }).click();

    const link = page.getByRole("link", { name: /myScheme पर और योजनाएँ देखें/ }).first();
    await expect(link).toContainText("Yojana Saathi ने इन्हें जाँचा नहीं है");
    await expect(link).toHaveAttribute("href", `${SEARCH}?keyword=Farmer`);
  });
});
