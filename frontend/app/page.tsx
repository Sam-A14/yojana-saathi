import { ChevronDown, ExternalLink, FileCheck, GraduationCap, HandHeart, KeyRound, ListChecks, ShieldCheck, Trash2, Users, Wheat } from "lucide-react";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { HeroPhone } from "@/components/landing/HeroPhone";
import { SchemesWeCheck } from "@/components/landing/SchemesWeCheck";
import { buttonClass } from "@/components/button-styles";
import { ButtonLink, Card } from "@/components/ui";

const GITHUB_URL = "https://github.com/Sam-A14/yojana-saathi";

function Section({ title, children, tone = "bg" }: { title: string; children: ReactNode; tone?: "bg" | "soft" }) {
  return (
    <section aria-label={title} className={tone === "soft" ? "bg-soft" : ""}>
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-14 md:py-20">
        <h2 className="display text-3xl md:text-4xl">{title}</h2>
        {children}
      </div>
    </section>
  );
}

function IconBubble({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
      {children}
    </span>
  );
}

export default async function Home() {
  const t = await getTranslations("home");
  const l = await getTranslations("landing");

  const steps = [
    { icon: <Users size={30} />, title: l("step1Title"), body: l("step1Body") },
    { icon: <ListChecks size={30} />, title: l("step2Title"), body: l("step2Body") },
    { icon: <FileCheck size={30} />, title: l("step3Title"), body: l("step3Body") },
  ];
  const people = [
    { icon: <GraduationCap size={30} />, title: l("studentsTitle"), example: l("studentsExample") },
    { icon: <Wheat size={30} />, title: l("farmersTitle"), example: l("farmersExample") },
    { icon: <HandHeart size={30} />, title: l("eldersTitle"), example: l("eldersExample") },
  ];
  const promises = [
    { icon: <ShieldCheck size={30} />, title: l("noAadhaarTitle"), body: l("noAadhaarBody") },
    { icon: <KeyRound size={30} />, title: l("noPasswordTitle"), body: l("noPasswordBody") },
    { icon: <Trash2 size={30} />, title: l("deleteTitle"), body: l("deleteBody") },
  ];
  const faq = [
    { q: l("faq1Q"), a: l("faq1A") },
    { q: l("faq2Q"), a: l("faq2A") },
    { q: l("faq3Q"), a: l("faq3A") },
    { q: l("faq4Q"), a: l("faq4A") },
    { q: l("faq5Q"), a: l("faq5A") },
  ];

  return (
    <>
      {/* The dramatic first screen: deep green, a marigold glow, a floating phone. Only this block is dark. */}
      <section className="on-dark relative overflow-hidden bg-hero text-on-hero">
        <div
          aria-hidden="true"
          className="glow pointer-events-none absolute -right-40 top-16 h-[32rem] w-[32rem] rounded-full"
          style={{ background: "radial-gradient(circle, rgb(245 158 11 / 0.35), transparent 65%)" }}
        />
        <div className="relative mx-auto grid w-full max-w-5xl items-center gap-12 px-4 pb-20 pt-10 md:grid-cols-[1.2fr_1fr] md:py-24">
          <div className="rise flex flex-col gap-6">
            <h1 className="display text-4xl sm:text-5xl md:text-6xl">{t("title")}</h1>
            <p className="text-xl text-on-hero-muted">{t("intro")}</p>
            <div className="flex flex-col gap-4 sm:flex-row md:flex-col lg:flex-row">
              <ButtonLink href="/setup/basics" variant="accent" className="w-full sm:w-auto">
                {t("start")}
              </ButtonLink>
              <ButtonLink href="/resume" variant="light" className="w-full sm:w-auto">
                {t("resume")}
              </ButtonLink>
            </div>
            <p className="text-lg font-semibold text-accent">{t("free")}</p>
          </div>
          <div className="rise" style={{ animationDelay: "0.15s" }}>
            <HeroPhone />
          </div>
        </div>
      </section>

      <Section title={l("howTitle")}>
        <ol className="grid gap-6 md:grid-cols-3">
          {steps.map((step, index) => (
            <li key={step.title}>
              <Card className="flex h-full flex-col gap-4">
                <div className="flex items-center gap-4">
                  <IconBubble>{step.icon}</IconBubble>
                  <span aria-hidden="true" className="display text-4xl text-accent-ink">
                    {index + 1}
                  </span>
                </div>
                <h3 className="text-xl font-bold">{step.title}</h3>
                <p className="text-lg">{step.body}</p>
              </Card>
            </li>
          ))}
        </ol>
      </Section>

      <Section title={l("whoTitle")} tone="soft">
        <ul className="grid gap-6 md:grid-cols-3">
          {people.map((person) => (
            <li key={person.title}>
              <Card className="flex h-full flex-col gap-4 transition duration-200 hover:-translate-y-1 hover:shadow-lift">
                <div className="flex items-center gap-4">
                  <IconBubble>{person.icon}</IconBubble>
                  <h3 className="text-xl font-bold">{person.title}</h3>
                </div>
                <p className="text-lg">{person.example}</p>
              </Card>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={l("schemesTitle")}>
        <p className="-mt-4 text-lg text-muted">{l("schemesIntro")}</p>
        <SchemesWeCheck />
      </Section>

      <Section title={l("privacyTitle")} tone="soft">
        <ul className="grid gap-6 md:grid-cols-3">
          {promises.map((item) => (
            <li key={item.title} className="flex flex-col gap-3">
              <div className="flex items-center gap-4">
                <IconBubble>{item.icon}</IconBubble>
                <h3 className="text-xl font-bold">{item.title}</h3>
              </div>
              <p className="text-lg">{item.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={l("faqTitle")}>
        {/* Plain <details>: opens and closes with no JavaScript, and works with a keyboard and screen reader. */}
        <div className="flex flex-col gap-4">
          {faq.map((item) => (
            <details key={item.q} className="group rounded-2xl border border-line-soft bg-surface shadow-card">
              <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 py-3 text-lg font-bold [&::-webkit-details-marker]:hidden">
                {item.q}
                <ChevronDown size={24} className="shrink-0 text-primary transition-transform duration-200 group-open:rotate-180" />
              </summary>
              <p className="px-5 pb-5 text-lg">{item.a}</p>
            </details>
          ))}
        </div>
      </Section>

      <Section title={l("aboutTitle")} tone="soft">
        <div className="flex max-w-2xl flex-col items-start gap-6">
          <p className="text-lg">{l("aboutBody")}</p>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className={buttonClass("secondary", "w-full sm:w-auto")}>
            {l("github")}
            <ExternalLink size={20} />
          </a>
        </div>
      </Section>
    </>
  );
}
