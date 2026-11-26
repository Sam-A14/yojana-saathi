import { Ban, CircleHelp, Clock, Code, Database, ExternalLink, Eye, ListChecks, Trash2 } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { IconSection } from "@/components/IconSection";
import { buttonClass } from "@/components/button-styles";
import { GITHUB_URL } from "@/lib/links";

// Public. Every sentence here is about what the app does today, checked against the backend code
// (see docs/decisions/025-privacy-page.md). No promise about anything not built, such as alerts.
const COLLECT = ["email", "language", "home", "people", "papers", "phone"] as const;
const SHARE = ["sell", "email", "hosting", "gov"] as const;
const KEEP = ["until", "code", "signedIn"] as const;
const STEPS = ["step1", "step2", "step3"] as const;

function List({ items }: { items: string[] }) {
  return (
    <ul className="flex list-disc flex-col gap-2 pl-6 text-lg">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default async function PrivacyPage() {
  const t = await getTranslations("privacyPage");
  const tl = await getTranslations("landing");
  return (
    <div className="flex flex-col gap-6">
      <h1 className="display text-3xl">{t("title")}</h1>
      <p className="text-lg">{t("intro")}</p>

      <IconSection title={t("collect.title")} icon={Database}>
        <p className="text-lg font-semibold">{t("collect.intro")}</p>
        <List items={COLLECT.map((key) => t(`collect.${key}`))} />
      </IconSection>

      <IconSection title={t("never.title")} icon={Ban}>
        <p className="text-lg">{t("never.body")}</p>
      </IconSection>

      <IconSection title={t("why.title")} icon={CircleHelp}>
        <p className="text-lg">{t("why.body")}</p>
      </IconSection>

      <IconSection title={t("how.title")} icon={ListChecks}>
        <List items={[t("how.rules"), t("how.noAi"), t("how.guidance")]} />
      </IconSection>

      <IconSection title={t("share.title")} icon={Eye}>
        <List items={SHARE.map((key) => t(`share.${key}`))} />
      </IconSection>

      <IconSection title={t("keep.title")} icon={Clock}>
        <List items={KEEP.map((key) => t(`keep.${key}`))} />
      </IconSection>

      <IconSection title={t("del.title")} icon={Trash2}>
        <ol className="flex list-decimal flex-col gap-2 pl-6 text-lg">
          {STEPS.map((key) => (
            <li key={key}>{t(`del.${key}`)}</li>
          ))}
        </ol>
        <p className="text-lg">{t("del.removes")}</p>
        <p className="text-lg">{t("del.limits")}</p>
        <p className="text-lg">{t("del.signOut")}</p>
      </IconSection>

      <IconSection title={t("code.title")} icon={Code}>
        <p className="text-lg">{t("code.body")}</p>
        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className={buttonClass("secondary", "w-full sm:w-auto sm:self-start")}>
          {tl("github")}
          <ExternalLink aria-hidden size={20} />
        </a>
      </IconSection>
    </div>
  );
}
