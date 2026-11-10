"use client";

import { useTranslations } from "next-intl";
import { ExampleBanner } from "@/components/ExampleBanner";
import { MemberResults } from "@/components/MemberResults";
import { EXAMPLE_DOCUMENTS, EXAMPLE_ELIGIBILITY, exampleSchemeHref } from "@/lib/example";

// A fixed, made-up family. No sign-in and no server call: people see the value before giving an email.
export default function ExamplePage() {
  const t = useTranslations("example");
  const td = useTranslations("dashboard");
  const all = EXAMPLE_ELIGIBILITY.members.flatMap((m) => m.schemes);
  const of = (status: string) => all.filter((s) => s.status === status).length;

  return (
    <div className="flex flex-col gap-6">
      <ExampleBanner />
      <h1 className="display text-3xl">{t("title")}</h1>
      <p className="text-lg">
        {td("summary", { fit: of("eligible"), close: of("near_miss"), unsure: of("unknown") })}
      </p>
      {EXAMPLE_ELIGIBILITY.members.map((member) => (
        <MemberResults
          key={member.member_id}
          member={member}
          documents={EXAMPLE_DOCUMENTS}
          schemeHref={exampleSchemeHref}
        />
      ))}
    </div>
  );
}
