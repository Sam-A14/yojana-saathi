"use client";

import { useParams, useSearchParams } from "next/navigation";
import { EXAMPLE_DOCUMENTS, EXAMPLE_ELIGIBILITY } from "@/lib/example";
import { ExampleBanner } from "./ExampleBanner";
import { SchemeDetail } from "./SchemeView";

/** One scheme of the example family: the real scheme page, fed with the fixed example data. */
export function ExampleScheme() {
  const { slug } = useParams<{ slug: string }>();
  const memberId = useSearchParams().get("member");
  return (
    <div className="flex flex-col gap-6">
      <ExampleBanner />
      <SchemeDetail
        eligibility={EXAMPLE_ELIGIBILITY}
        documents={EXAMPLE_DOCUMENTS}
        slug={slug}
        memberId={memberId}
        backHref="/example"
      />
    </div>
  );
}
