"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Button, ButtonLink, ErrorNote, TextField } from "@/components/ui";
import { ApiError, api, errorKind } from "@/lib/api";
import { nextPathFor } from "@/lib/next-path";
import { saveSession, useSession } from "@/lib/session";

// The same shape check as the server's: the only real test is that the code arrives.
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

export default function SignInPage() {
  const t = useTranslations("signin");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const router = useRouter();
  const { ready, session } = useSession();

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

  if (!ready || session) return <p role="status">{tc("loading")}</p>;

  if (step === "code") {
    return (
      <form onSubmit={verify} className="flex flex-col gap-6" noValidate>
        <h1 className="display text-3xl">{t("codeTitle")}</h1>
        <p className="text-lg">{t("codeIntro", { email })}</p>
        <p className="text-base text-muted">{t("spam")}</p>
        <TextField
          label={t("codeLabel")}
          value={code}
          // No maxLength on the box: it would cut "123 456" (pasted with a space) to 5 digits before
          // this filter keeps the first six digits.
          onChange={(value) => setCode(value.replace(/\D/g, "").slice(0, 6))}
          inputMode="numeric"
          autoComplete="one-time-code"
          error={null}
          className="tracking-[0.4em]"
        />
        {notice && <p role="status" className="font-semibold text-primary">{notice}</p>}
        {problem && <ErrorNote>{problem}</ErrorNote>}
        <Button type="submit" disabled={busy || code.length !== 6} className="w-full">
          {busy ? t("verifying") : t("verify")}
        </Button>
        <div className="flex flex-col gap-3">
          <Button variant="secondary" onClick={resend} disabled={busy}>
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
      <h1 className="display text-3xl">{t("title")}</h1>
      <p className="text-lg">{t("intro")}</p>
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
      <p className="text-base text-muted">{t("privacy")}</p>
      {problem && <ErrorNote>{problem}</ErrorNote>}
      <Button type="submit" disabled={busy || email.trim() === ""} className="w-full">
        {busy ? t("sending") : t("send")}
      </Button>
      <ButtonLink href="/" variant="secondary">
        {tc("back")}
      </ButtonLink>
    </form>
  );
}
