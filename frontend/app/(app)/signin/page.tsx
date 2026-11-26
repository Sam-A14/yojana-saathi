"use client";

import { KeyRound, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { OtpInput } from "@/components/OtpInput";
import { Button, ButtonLink, Card, ErrorNote, Skeleton, TextField } from "@/components/ui";
import { ApiError, api, errorKind } from "@/lib/api";
import { nextPathFor } from "@/lib/next-path";
import { saveSession, useSession } from "@/lib/session";
import { useCountdown } from "@/lib/use-countdown";

// The same shape check as the server's: the only real test is that the code arrives.
// How long "Send me a new code" waits after a code was sent. Only a convenience against double taps
// and an impatient second request: the server has its own limits (per email per hour, and a daily
// cap) and does not rely on this.
const RESEND_WAIT_SECONDS = 30;

const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

// The reasons the sign-in endpoints can give (detail.code), each with its own plain message.
const KNOWN = [
  "invalid_code",
  "code_expired",
  "too_many_attempts",
  "too_many_codes",
  "busy",
  "email_failed",
] as const;
type Known = (typeof KNOWN)[number];
const isKnown = (code: string | null): code is Known => KNOWN.some((known) => known === code);

/** The round picture above the title. The title right below it says what it means. */
function IconTile({ children }: { children: React.ReactNode }) {
  return (
    <span aria-hidden className="pop flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-soft text-primary shadow-card">
      {children}
    </span>
  );
}

export default function SignInPage() {
  const t = useTranslations("signin");
  const tp = useTranslations("privacyPage");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const router = useRouter();
  const { ready, session } = useSession();
  const wait = useCountdown(RESEND_WAIT_SECONDS);

  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  // Signed in (just now, or earlier): go where the app goes next. The guard stops a second request
  // when the session text changes while we are still asking the server.
  const routing = useRef<string | null>(null);
  useEffect(() => {
    if (!ready || !session || routing.current === session.token) return;
    routing.current = session.token;
    nextPathFor(session)
      .then((path) => router.replace(path))
      .catch(() => router.replace("/dashboard")); // the dashboard shows the problem and a retry
  }, [ready, session, router]);

  function describe(error: unknown): string {
    if (error instanceof ApiError && isKnown(error.code)) {
      const text = t(error.code);
      return error.attemptsLeft !== null && error.code === "invalid_code"
        ? `${text} ${t("attemptsLeft", { count: error.attemptsLeft })}`
        : text;
    }
    const kind = errorKind(error);
    return te(kind === "network" ? "network" : "generic");
  }

  async function sendCode(event?: FormEvent) {
    event?.preventDefault();
    const address = email.trim().toLowerCase(); // the server does the same, so one person is one account
    if (!EMAIL_SHAPE.test(address)) {
      setProblem(t("invalidEmail"));
      return;
    }
    setBusy(true);
    setProblem(null);
    setNotice(null);
    try {
      await api.requestCode(address, locale);
      setEmail(address);
      wait.restart();
      setStep("code");
    } catch (error) {
      setProblem(describe(error));
    }
    setBusy(false);
  }

  async function resend() {
    setBusy(true);
    setProblem(null);
    setNotice(null);
    try {
      await api.requestCode(email, locale);
      wait.restart();
      setCode("");
      setNotice(t("resent"));
    } catch (error) {
      setProblem(describe(error));
    }
    setBusy(false);
  }

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setProblem(t("invalidCodeShape"));
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      const opened = await api.verifyCode(email, code);
      saveSession({ token: opened.access_token, email, householdId: null });
      // This page is kept (hidden) by Next.js. On a shared phone the next person must not find
      // the email or the code in the boxes.
      setStep("email");
      setEmail("");
      setCode("");
      setNotice(null);
    } catch (error) {
      setProblem(describe(error));
    }
    setBusy(false);
  }

  if (!ready || session) return <Skeleton label={tc("loading")} />;

  if (step === "code") {
    return (
      <form onSubmit={verify} className="flex flex-col gap-6" noValidate>
        <IconTile><KeyRound size={30} /></IconTile>
        <h1 className="page-title">{t("codeTitle")}</h1>
        <p className="text-lg">{t("codeIntro", { email })}</p>
        <p className="text-base text-muted">{t("spam")}</p>
        <Card className="flex flex-col gap-6">
        <OtpInput label={t("codeLabel")} value={code} onChange={setCode} />
        {notice && <p role="status" className="font-semibold text-primary">{notice}</p>}
        {problem && <ErrorNote>{problem}</ErrorNote>}
        <Button type="submit" disabled={busy || code.length !== 6} className="w-full">
          {busy ? t("verifying") : t("verify")}
        </Button>
        </Card>
        <div className="flex flex-col gap-3">
          {/* The number on screen changes every second, so it is hidden from screen readers; they
              get one sentence when the wait starts and one when it ends. */}
          <p aria-hidden className="text-base font-semibold text-muted">
            {wait.left > 0 ? t("resendWait", { seconds: wait.left }) : t("resendReady")}
          </p>
          <p role="status" className="sr-only">
            {wait.left > 0 ? t("resendWait", { seconds: RESEND_WAIT_SECONDS }) : t("resendReady")}
          </p>
          <Button variant="secondary" onClick={resend} disabled={busy || wait.left > 0}>
            {t("resend")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setStep("email");
              setCode("");
              setProblem(null);
              setNotice(null);
            }}
            disabled={busy}
          >
            {t("otherEmail")}
          </Button>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={sendCode} className="flex flex-col gap-6" noValidate>
      <IconTile><Mail size={30} /></IconTile>
      <h1 className="page-title">{t("title")}</h1>
      <p className="text-lg">{t("intro")}</p>
      {/* Sign-in options live in this one block. A future "Continue with Google" button and an "or"
          divider go ABOVE this card, so nothing below has to be moved. Not built yet, so nothing is
          shown for it. */}
      <Card className="flex flex-col gap-6">
      <TextField
        label={t("emailLabel")}
        hint={t("emailHint")}
        value={email}
        onChange={setEmail}
        type="email"
        inputMode="email"
        autoComplete="email"
        autoCapitalize="off"
        spellCheck={false}
      />
      {problem && <ErrorNote>{problem}</ErrorNote>}
      <Button type="submit" disabled={busy || email.trim() === ""} className="w-full">
        {busy ? t("sending") : t("send")}
      </Button>
      </Card>
      <p className="flex items-start gap-3 text-base text-muted">
        <ShieldCheck aria-hidden size={24} className="mt-0.5 shrink-0 text-primary" />
        {t("privacy")}
      </p>
      <Link href="/privacy" className="inline-flex min-h-12 items-center text-lg font-bold text-primary underline">
        {tp("link")}
      </Link>
      <ButtonLink href="/" variant="secondary">
        {tc("back")}
      </ButtonLink>
    </form>
  );
}
