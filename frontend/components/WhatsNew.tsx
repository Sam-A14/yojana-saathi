"use client";

import { Bell } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { alertText, unreadCount } from "@/lib/alerts";
import { formatDate } from "@/lib/format";
import type { AlertItem, Family } from "@/lib/types";
import { Button, Card } from "./ui";

/** "What's new for your family": the news the daily job found (a scheme that now fits, an age
 * coming up, a scheme whose rules changed). Read-only apart from "Mark as read". If the list cannot
 * be loaded nothing is shown: the results below are what the family came for. */
export function WhatsNew({ family }: { family: Family }) {
  const t = useTranslations("alerts");
  const locale = useLocale() === "hi" ? "hi" : "en";
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getAlerts(family)
      .then((found) => !cancelled && setAlerts(found.alerts))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [family]);

  if (failed || alerts === null) return null;
  const unread = unreadCount(alerts);

  async function markRead(id: number) {
    try {
      await api.markAlertRead(family, id);
      setAlerts((list) => list?.map((a) => (a.id === id ? { ...a, read: true } : a)) ?? null);
    } catch {
      setFailed(true); // the list may be stale: hide it rather than show a wrong "new"
    }
  }

  async function markAllRead() {
    try {
      const found = await api.markAllAlertsRead(family);
      setAlerts(found.alerts);
    } catch {
      setFailed(true);
    }
  }

  return (
    <section aria-labelledby="whats-new-title">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="whats-new-title" className="flex items-center gap-2 text-2xl font-bold">
            <Bell aria-hidden size={24} />
            {t("title")}
          </h2>
          {unread > 0 && <span className="rounded-full bg-accent px-3 py-1 text-base font-bold text-on-accent">{t("unread", { count: unread })}</span>}
        </div>
        {alerts.length === 0 ? (
          <p className="mt-3 text-lg">{t("empty")}</p>
        ) : (
          <>
            <ul className="mt-3 flex flex-col gap-3">
              {alerts.map((alert) => {
                const { key, values } = alertText(alert, locale);
                return (
                  <li key={alert.id} className={`flex flex-col gap-2 rounded-xl border-2 p-4 ${alert.read ? "border-line" : "border-accent-ink bg-soft"}`}>
                    <p className="text-lg">
                      {!alert.read && <strong>{t("new")}: </strong>}
                      {t(`text.${key}`, values)}
                    </p>
                    <p className="text-base text-muted">{formatDate(alert.created_at, locale)}</p>
                    {!alert.read && (
                      <Button variant="secondary" onClick={() => markRead(alert.id)} className="self-start">
                        {t("markRead")}
                      </Button>
                    )}
                  </li>
                );
              })}
            </ul>
            {unread > 1 && (
              <Button variant="secondary" onClick={markAllRead} className="mt-3 self-start">
                {t("markAllRead")}
              </Button>
            )}
          </>
        )}
      </Card>
    </section>
  );
}
