"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "./ui";

/** Edit and Remove for one person's card. Each button has an icon AND a word (the icon alone would
 * not say what it does), and is a full-size target. Remove never acts at once: it asks first. */
export function MemberActions({
  name,
  busy,
  onEdit,
  onRemove,
}: {
  name: string;
  busy: boolean;
  onEdit: () => void;
  onRemove: () => void;
}) {
  const t = useTranslations("members");
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <div role="group" aria-label={t("removeConfirm", { name })} className="flex flex-col gap-3 border-t border-line-soft pt-4">
        <p className="text-lg font-semibold">{t("removeConfirm", { name })}</p>
        <Button
          variant="danger"
          disabled={busy}
          onClick={() => {
            setConfirming(false);
            onRemove();
          }}
        >
          <Trash2 aria-hidden size={22} />
          {t("removeYes")}
        </Button>
        <Button variant="secondary" onClick={() => setConfirming(false)}>
          {t("removeKeep")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex gap-3 border-t border-line-soft pt-4">
      <Button variant="secondary" className="flex-1" disabled={busy} onClick={onEdit} aria-label={`${t("edit")}: ${name}`}>
        <Pencil aria-hidden size={20} />
        {t("edit")}
      </Button>
      <Button variant="secondary" className="flex-1" disabled={busy} onClick={() => setConfirming(true)} aria-label={`${t("remove")}: ${name}`}>
        <Trash2 aria-hidden size={20} />
        {t("remove")}
      </Button>
    </div>
  );
}
