"use client";

import { useEffect, useState } from "react";

type BackendStatus =
  | { state: "checking" }
  | { state: "ok"; version: string }
  | { state: "down" };

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export default function Home() {
  const [backend, setBackend] = useState<BackendStatus>({ state: "checking" });

  // Called from the browser on purpose: it proves the backend's CORS setting works.
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(res.statusText))))
      .then((data: { status: string; version: string }) =>
        setBackend(data.status === "ok" ? { state: "ok", version: data.version } : { state: "down" }),
      )
      .catch(() => setBackend({ state: "down" }));
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-4xl font-semibold tracking-tight">Yojana Saathi</h1>
      <p className="text-lg text-zinc-600 dark:text-zinc-400">
        Set up your family once. See every government scheme each member may qualify for, and which
        documents are still missing.
      </p>

      <p className="rounded-lg border border-zinc-200 px-4 py-3 text-base dark:border-zinc-800">
        {backend.state === "checking" && "Backend: checking… (the first call can take a minute)"}
        {backend.state === "ok" && `Backend: ok (version ${backend.version})`}
        {backend.state === "down" && "Backend: not reachable"}
      </p>

      <p className="text-sm text-zinc-500">
        Guidance only, not an official decision. Not a government app.
      </p>
    </main>
  );
}
