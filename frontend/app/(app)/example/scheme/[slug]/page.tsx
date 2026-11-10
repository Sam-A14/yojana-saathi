import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { ExampleScheme } from "@/components/ExampleScheme";

// The client view reads the ?member= query, which needs a Suspense boundary around it.
export default async function ExampleSchemePage() {
  const t = await getTranslations("scheme");
  return (
    <Suspense fallback={<p role="status">{t("loading")}</p>}>
      <ExampleScheme />
    </Suspense>
  );
}
