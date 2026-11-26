import type { ReactNode } from "react";

/** The frame of every app page (everything except the home page): a soft teal band with a curved
 * bottom edge behind the page title, then the content in a centred column.
 * "narrow" (forms, privacy, one scheme) is a comfortable line length for reading aloud;
 * "wide" (the lists of schemes and of family members) has room for two columns on a tablet.
 *
 * min-h-svh: these screens first show "Loading…" and then grow. A column as tall as the screen keeps
 * the footer below the fold the whole time, so it is not pushed down later (decision 021). */
export function PageFrame({ width, children }: { width: "narrow" | "wide"; children: ReactNode }) {
  return (
    <div className="relative isolate">
      {/* Decoration only, behind the content, so it can never move anything. */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-10 h-44 bg-band"
        style={{ borderRadius: "0 0 50% 50% / 0 0 3rem 3rem" }}
      />
      <div className={`mx-auto min-h-svh w-full px-4 py-8 ${width === "wide" ? "max-w-5xl" : "max-w-xl"}`}>{children}</div>
    </div>
  );
}
