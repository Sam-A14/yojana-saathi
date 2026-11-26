import { expect, test } from "@playwright/test";
import { avatarColour, initials } from "../../lib/initials";

test.describe("the letters in a person's avatar", () => {
  test("first letter of the first and last word", () => {
    expect(initials("Asha Devi")).toBe("AD");
    expect(initials("ramesh kumar singh")).toBe("RS");
  });

  test("one word gives one letter, no name gives a question mark", () => {
    expect(initials("Asha")).toBe("A");
    expect(initials("   ")).toBe("?");
  });

  test("Hindi letters keep their vowel signs", () => {
    // "कृ" is क + a vowel sign: taking name[0] would cut it down to "क".
    // "देवी" also starts with a vowel sign (दे), so that stays whole too.
    expect(initials("कृष्णा देवी")).toBe("कृदे");
    expect(initials("रमेश")).toBe("र");
  });

  test("the same name always gets the same colour, and it is one of the five", () => {
    expect(avatarColour("Asha")).toBe(avatarColour("Asha"));
    for (const name of ["Asha", "Ramesh", "Gudiya", "कमला", "x"]) {
      expect(avatarColour(name)).toBeGreaterThanOrEqual(0);
      expect(avatarColour(name)).toBeLessThan(5);
    }
  });
});
