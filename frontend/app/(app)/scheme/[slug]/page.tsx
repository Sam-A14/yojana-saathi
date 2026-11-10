import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { SchemeView } from "@/components/SchemeView";

// The client view reads the ?member= query, which needs a Suspense boundary around it.
export default async function SchemePage() {
  const t = await getTranslations("scheme");
  return (
    <Suspense fallback={<p role="status">{t("loading")}</p>}>
      <SchemeView />
    </Suspense>
  );
}
