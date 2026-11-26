import type { ReactNode } from "react";

// Setup, dashboard and scheme screens stay in one narrow column that works with a thumb. The home
// page sits outside this group because it needs the full width.
//
// min-h-svh: these screens first show "Loading…" and then grow. With a short page the footer sat on
// the first screen and was pushed off it when the content arrived, which Lighthouse counted as a
// 0.145 layout shift. A full-screen-tall column keeps the footer below the fold the whole time.
export default function AppLayout({ children }: { children: ReactNode }) {
  return <div className="mx-auto min-h-svh w-full max-w-xl px-4 py-6">{children}</div>;
}
