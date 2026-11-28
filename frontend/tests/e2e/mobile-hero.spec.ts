import { type Page } from "@playwright/test";
import { expect, test } from "./fixtures";

// PR 3 of the portal redesign: a compact header and hero on a phone (decision 026). The family photo
// must start inside the first screen of a 844px-tall phone, with the text at the normal size (A).
const WIDTHS = [360, 375, 390, 412, 430];

async function numbers(page: Page) {
  return page.evaluate(() => {
    const box = (el: Element) => el.getBoundingClientRect();
    const h1 = document.querySelector("h1")!;
    const photo = document.querySelector("main img")!;
    const cta = [...document.querySelectorAll("main a")].find((a) => a.getAttribute("href") === "/setup/basics")!;
    const controls = [...document.querySelectorAll("header button, header a")].filter((e) => (e as HTMLElement).offsetParent !== null);
    return {
      header: box(document.querySelector("header")!).height,
      strip: box(document.querySelector("header")!.firstElementChild!).height,
      h1Size: parseFloat(getComputedStyle(h1).fontSize),
      h1Lines: Math.round(box(h1).height / parseFloat(getComputedStyle(h1).lineHeight)),
      ctaHeight: box(cta).height,
      ctaWidth: box(cta).width,
      ctaBottom: box(cta).bottom + scrollY,
      photoTop: box(photo).top + scrollY,
      smallestControl: Math.min(...controls.map((e) => box(e).height)),
      sideways: document.documentElement.scrollWidth > innerWidth,
      viewport: innerWidth,
    };
  });
}

for (const width of WIDTHS) {
  test(`${width}px phone: compact header, 3-line headline, full-width button, photo in the first screen`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/");
    const n = await numbers(page);

    expect(n.header, "whole header").toBeLessThanOrEqual(130);
    expect(n.strip, "toolbar row").toBeLessThanOrEqual(62);
    expect(n.smallestControl, "every header control is at least 48px tall").toBeGreaterThanOrEqual(48);
    expect(n.h1Size).toBeGreaterThanOrEqual(38);
    expect(n.h1Size).toBeLessThanOrEqual(43);
    expect(n.h1Lines).toBe(3);
    expect(n.ctaHeight).toBeGreaterThanOrEqual(56);
    expect(n.ctaHeight).toBeLessThanOrEqual(62);
    expect(n.ctaWidth / width, "the button spans the screen").toBeGreaterThan(0.85);
    expect(n.photoTop, "the photo starts inside the first screen").toBeLessThan(844);
    expect(n.photoTop - n.ctaBottom, "the photo follows the button directly").toBeLessThanOrEqual(40);
    expect(n.sideways).toBe(false);
  });
}

test("in Hindi and with larger text nothing runs off the side and the photo is still in the first screen", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("yojana.textSize", "large"));
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/");
    await page.getByRole("button", { name: "हिन्दी" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    const n = await numbers(page);
    expect(n.sideways, `${width}px`).toBe(false);
    expect(n.smallestControl, `${width}px`).toBeGreaterThanOrEqual(48);
    expect(n.photoTop, `${width}px`).toBeLessThan(844);
  }
});

test("on a phone the free line and the two quiet links come after the photo, once each", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const photo = await page.getByRole("img", { name: /family of several generations/ }).boundingBox();
  // In <main>, exact: the header has its own "Sign in" button, which is hidden on a phone.
  for (const name of ["Try a demo family", "Sign in"]) {
    const link = page.getByRole("main").getByRole("link", { name, exact: true });
    await expect(link).toHaveCount(1); // the other copy is display:none, so it is not in the accessibility tree
    expect((await link.boundingBox())!.y).toBeGreaterThan(photo!.y + photo!.height);
  }
});

test("from 720px up the layout is the one before: the links sit under the button, beside the photo", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  const photo = await page.getByRole("img", { name: /family of several generations/ }).boundingBox();
  const link = page.getByRole("link", { name: "Try a demo family" });
  await expect(link).toHaveCount(1);
  const box = (await link.boundingBox())!;
  expect(box.x + box.width).toBeLessThan(photo!.x); // in the left column, beside the photo
  const cta = (await page.getByRole("link", { name: "Find schemes for my family" }).boundingBox())!;
  expect(box.y).toBeGreaterThan(cta.y + cta.height); // under the main button
});
