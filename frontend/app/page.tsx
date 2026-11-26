import { CalendarCheck, ChevronDown, ExternalLink, FileCheck, Link2, ListChecks, ShieldCheck, Users } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { buttonClass } from "@/components/button-styles";
import { CategoryCards } from "@/components/landing/CategoryCards";
import { WarmUp } from "@/components/landing/WarmUp";
import { ButtonLink, Card } from "@/components/ui";
import { GITHUB_URL } from "@/lib/links";

// id: the header's "How it works", "FAQ" and "About" links jump here. scroll-mt keeps the heading clear of the top edge.
function Section({ id, title, children, tone = "bg" }: { id?: string; title: string; children: ReactNode; tone?: "bg" | "soft" }) {
  return (
    <section id={id} aria-label={title} className={`scroll-mt-4 ${tone === "soft" ? "bg-soft" : ""}`}>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-14 md:py-20">
        <h2 className="display text-3xl md:text-4xl">{title}</h2>
        {children}
      </div>
    </section>
  );
}

function IconBubble({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-teal-soft text-teal">{children}</span>
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
  // Honest wording only. Each sentence describes something the app does today (decision 026).
  const trust = [
    { icon: <Link2 aria-hidden size={28} />, text: l("trust1") },
    { icon: <CalendarCheck aria-hidden size={28} />, text: l("trust2") },
    { icon: <ShieldCheck aria-hidden size={28} />, text: l("trust3") },
  ];
  const faq = [
    { q: l("faq1Q"), a: l("faq1A") },
    { q: l("faq2Q"), a: l("faq2A") },
    { q: l("faq3Q"), a: l("faq3A") },
    { q: l("faq4Q"), a: l("faq4A") },
    { q: l("faq5Q"), a: l("faq5A") },
  ];
  const textLink = "inline-flex min-h-12 items-center text-lg font-bold text-primary underline underline-offset-4";

  return (
    <>
      <WarmUp />
      <section className="relative overflow-hidden bg-surface">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{ background: "radial-gradient(circle at 88% 18%, var(--teal-soft), transparent 55%)" }}
        />
        <div className="relative mx-auto grid w-full max-w-6xl items-center gap-10 px-4 pb-24 pt-10 md:grid-cols-2 md:gap-12 md:pb-32 md:pt-16">
          <div className="flex flex-col gap-6">
            <h1 className="display text-4xl sm:text-5xl lg:text-6xl">{t("title")}</h1>
            {/* A short gold bar: the one decorative use of the highlight colour in the hero. */}
            <span aria-hidden="true" className="-mt-2 h-1.5 w-24 rounded-full bg-accent" />
            <p className="text-xl text-muted">{t("intro")}</p>
            <div className="flex flex-col gap-3">
              <ButtonLink href="/setup/basics" className="w-full sm:w-auto sm:self-start">
                {t("start")}
              </ButtonLink>
              <p className="text-lg font-semibold text-accent-ink">{t("free")}</p>
              <div className="flex flex-col sm:flex-row sm:gap-8">
                <Link href="/example" className={textLink}>
                  {t("example")}
                </Link>
                <Link href="/signin" className={textLink}>
                  {t("signIn")}
                </Link>
              </div>
            </div>
          </div>
          {/* The photo: below the buttons on a phone, in the right half on a computer. 4:3 trims only the
              sides, and every face stays inside the crop (checked at 360px). No caption: it must not read
              as these people using or endorsing the app. loading="eager" without `priority`: on a phone it is below
              the fold, and preloading it slowed the headline (Lighthouse LCP) by about 150 ms. */}
          <div className="relative">
            <span aria-hidden="true" className="absolute -bottom-3 -left-3 h-2/3 w-2/3 rounded-[2rem] bg-accent/70" />
            <Image
              src="/images/hero-family.jpg"
              alt={t("photoAlt")}
              width={2400}
              height={1600}
              loading="eager"
              sizes="(min-width: 1296px) 600px, (min-width: 768px) 46vw, 100vw"
              className="relative aspect-[4/3] w-full rounded-[2rem] object-cover shadow-lift"
              style={{ objectPosition: "50% 30%" }}
            />
          </div>
        </div>
        {/* The curve into the next section: the same colour as that section (--soft). */}
        <svg aria-hidden="true" viewBox="0 0 1440 90" preserveAspectRatio="none" className="absolute inset-x-0 bottom-0 block h-12 w-full text-soft md:h-20">
          <path fill="currentColor" d="M0 90V46C240 6 480 0 720 24c240 24 480 40 720 -4V90Z" />
        </svg>
      </section>

      <section aria-label={l("categoriesTitle")} className="bg-soft">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 pb-14 pt-4 md:pb-20">
          <div className="flex flex-col gap-3">
            <h2 className="display text-3xl md:text-4xl">{l("categoriesTitle")}</h2>
            <p className="text-lg text-muted">{l("categoriesIntro")}</p>
          </div>
          <CategoryCards />
          <ButtonLink href="/schemes" variant="secondary" className="w-full sm:w-auto sm:self-start">
            {l("seeAllSchemes")}
          </ButtonLink>
        </div>
      </section>

      <Section id="how" title={l("howTitle")}>
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

      <section aria-label={l("trustTitle")} className="on-dark bg-hero text-on-hero">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-14">
          <h2 className="display text-3xl">{l("trustTitle")}</h2>
          <ul className="grid gap-6 md:grid-cols-3">
            {trust.map((item) => (
              <li key={item.text} className="flex items-start gap-4">
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-accent text-on-accent">{item.icon}</span>
                <p className="text-lg font-semibold">{item.text}</p>
              </li>
            ))}
          </ul>
          <p className="max-w-3xl text-lg text-on-hero-muted">{l("emailPromise")}</p>
          <Link href="/privacy" className="inline-flex min-h-12 items-center text-lg font-bold underline underline-offset-4">
            {l("privacyLink")}
          </Link>
        </div>
      </section>

      <Section id="faq" title={l("faqTitle")}>
        {/* Plain <details>: opens and closes with no JavaScript, and works with a keyboard and screen reader. */}
        <div className="flex max-w-3xl flex-col gap-4">
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

      <Section id="about" title={l("aboutTitle")} tone="soft">
        <div className="flex max-w-2xl flex-col items-start gap-6">
          <p className="text-lg">{l("aboutBody")}</p>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className={buttonClass("secondary", "w-full sm:w-auto")}>
            {l("github")}
            <ExternalLink aria-hidden size={20} />
          </a>
        </div>
      </Section>
    </>
  );
}
