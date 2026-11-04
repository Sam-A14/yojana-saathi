"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { documentName } from "@/lib/format";
import { type NeededAnswers as Needed } from "@/lib/rules";
import { useText } from "@/lib/use-text";
import type { DocumentInfo } from "@/lib/types";

/**
 * Why a result is "unknown" and what would settle it: the questions the family can answer (with a
 * link to the setup screen where they can), and the plain-words reason when only an exact age or
 * income would settle it, which the family cannot give us.
 */
export function NeededAnswers({
  needed,
  memberName,
  documents,
}: {
  needed: Needed;
  memberName: string;
  documents: DocumentInfo[];
}) {
  const t = useTranslations("needs");
  const text = useText();
  const locale = useLocale() === "hi" ? "hi" : "en";

  function question(field: string, familyWide: boolean): string {
    const name = familyWide ? t("everyone") : memberName;
    if (field.startsWith("has_")) {
      const document = documentName(documents, field.slice(4), locale);
      return text("questions.document", { name, document });
    }
    return text(`questions.${field}`, { name });
  }

  return (
    <div className="flex flex-col gap-3">
      {needed.reasons.map((reason) => (
        <p key={reason}>
          {reason === "depends_on_exact_age" ? t("reasonAge") : t("reasonIncome")} {t("checkOfficial")}
        </p>
      ))}
      {needed.needs.length > 0 && (
        <div>
          <p className="font-semibold">{t("title")}</p>
          <ul className="mt-2 flex flex-col gap-2">
            {needed.needs.map((need) => (
              <li key={need.field} className="flex flex-col gap-1">
                <span>{question(need.field, need.familyWide)}</span>
                {need.link && (
                  <Link href={need.link} className="min-h-12 self-start py-3 font-semibold underline">
                    {t("answer")}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
