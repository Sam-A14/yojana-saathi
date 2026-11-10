import type { ReactNode } from "react";

// Setup, dashboard and scheme screens stay in one narrow column that works with a thumb. The home
// page sits outside this group because it needs the full width.
export default function AppLayout({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-xl px-4 py-6">{children}</div>;
}
