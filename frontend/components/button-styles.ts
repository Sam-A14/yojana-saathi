// Button looks live in a plain file (not "use client") so server pages can use buttonClass() too.
// Colours come from the tokens in globals.css, so dark mode needs no extra classes.

export const buttonBase =
  "inline-flex min-h-14 items-center justify-center gap-2 rounded-xl px-6 text-lg font-bold transition duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50";
export const buttonLook = {
  primary: "bg-primary text-on-primary shadow-card hover:bg-primary-hover",
  // Marigold: for the one main action on a dark background (the home page hero).
  accent: "bg-accent text-on-accent shadow-lift hover:bg-accent-hover",
  secondary: "border-2 border-primary text-primary hover:bg-primary-soft",
  // The outline button on the dark hero.
  light: "border-2 border-on-hero text-on-hero hover:bg-on-hero/10",
  danger: "border-2 border-danger text-danger hover:bg-danger-bg",
};
export type Look = keyof typeof buttonLook;

/** The look of a button, for places that need a real link (an official website opens in a new tab). */
export const buttonClass = (variant: Look = "primary", extra = "") =>
  `${buttonBase} ${buttonLook[variant]} ${extra}`;

