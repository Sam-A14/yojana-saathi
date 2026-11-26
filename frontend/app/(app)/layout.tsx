import type { ReactNode } from "react";
import { PageFrame } from "@/components/PageFrame";

// Setup, sign-in, privacy and scheme screens stay in one narrow column that works with a thumb. The
// home page sits outside this group because it needs the full width; the list pages (schemes,
// dashboard, example) are in the sibling group app/(wide)/. Route groups do not change any URL.
export default function AppLayout({ children }: { children: ReactNode }) {
  return <PageFrame width="narrow">{children}</PageFrame>;
}
