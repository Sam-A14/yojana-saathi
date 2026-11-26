// Where the colour theme choice is remembered on this phone, and the three choices. In its own
// file because the layout (a server file) and the toggle (a client file) both need it.
export const THEME_KEY = "yojana.theme";
export const THEMES = ["light", "dark", "device"] as const;
export type Theme = (typeof THEMES)[number];

/** Anything that is not a known choice (nothing saved, or a stale value) means Light. */
export function toTheme(value: string | null | undefined): Theme {
  return THEMES.find((theme) => theme === value) ?? "light";
}
