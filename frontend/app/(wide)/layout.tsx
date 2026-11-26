import type { ReactNode } from "react";
import { PageFrame } from "@/components/PageFrame";

// The pages that list several things (schemes, family members) get a wider column, so on a tablet
// or computer the cards sit two to a row. Same look as app/(app)/layout.tsx otherwise.
export default function WideLayout({ children }: { children: ReactNode }) {
  return <PageFrame width="wide">{children}</PageFrame>;
}
