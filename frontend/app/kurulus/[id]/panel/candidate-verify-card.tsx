"use client";

import { useState } from "react";
import { PanelIcon, SideCard, actionClass } from "@/components/panel-kit";
import { Alert } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import messages from "@/messages/tr.json";
import { candidateHref, parseCandidateLink } from "./candidate-link";
import { FIELD_CLASS, LABEL_CLASS } from "./ui";

const t = messages.kurulusPanel.candidate;

/** Paste a CV link; the record opens on our own origin (only the path is used). */
export function CandidateVerifyCard() {
  const [value, setValue] = useState("");
  const [feedback, setFeedback] = useState<{ kind: "error" | "info"; text: string } | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const link = parseCandidateLink(value);
    if (!link) {
      setFeedback({ kind: "error", text: t.invalid });
      return;
    }
    window.open(candidateHref(link), "_blank", "noopener,noreferrer");
    setFeedback({ kind: "info", text: t.opened });
  };

  return (
    <SideCard title={t.title} hint={t.hint}>
      <form onSubmit={submit} className="space-y-3" noValidate>
        <div>
          <label htmlFor="candidate-link" className={LABEL_CLASS}>
            {t.label}
          </label>
          <input
            id="candidate-link"
            type="text"
            inputMode="url"
            autoComplete="off"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setFeedback(null);
            }}
            placeholder={t.placeholder}
            aria-invalid={feedback?.kind === "error" ? true : undefined}
            aria-describedby={feedback ? "candidate-link-feedback" : undefined}
            className={FIELD_CLASS}
          />
        </div>
        <button type="submit" className={cn(actionClass.neutral, "w-full")}>
          <PanelIcon name="search" className="h-4 w-4" />
          {t.button}
        </button>
        <div id="candidate-link-feedback" aria-live="polite">
          {feedback ? (
            <Alert variant={feedback.kind === "error" ? "error" : "info"} className="text-sm">
              {feedback.text}
            </Alert>
          ) : null}
        </div>
      </form>
    </SideCard>
  );
}
