import { expect, test } from "@playwright/test";
import { readClientId } from "../../lib/google";

// "Hide the button when the client ID is missing" rests on this one function.
test.describe("the Google client ID setting", () => {
  test("missing, empty or only spaces means Google sign-in is off", () => {
    expect(readClientId(undefined)).toBeNull();
    expect(readClientId("")).toBeNull();
    expect(readClientId("   ")).toBeNull();
  });

  test("a real ID is kept, without stray spaces or a trailing newline", () => {
    expect(readClientId("123-abc.apps.googleusercontent.com")).toBe("123-abc.apps.googleusercontent.com");
    expect(readClientId(" 123-abc.apps.googleusercontent.com\n")).toBe("123-abc.apps.googleusercontent.com");
  });
});
