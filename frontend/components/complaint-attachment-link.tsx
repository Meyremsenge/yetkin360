"use client";

import { useState } from "react";
import { getAttachmentDownloadUrl } from "@/lib/api/complaints";

interface ComplaintAttachmentLinkProps {
  complaintId: string;
  attachmentId: string;
  label: string;
  errorText: string;
  admin?: boolean;
}

/**
 * The download endpoint answers JSON with a short-lived signed URL, so a plain
 * href would show JSON. The tab is opened synchronously (popup blockers) and
 * pointed at the URL once it resolves.
 */
export function ComplaintAttachmentLink({
  complaintId,
  attachmentId,
  label,
  errorText,
  admin = false,
}: ComplaintAttachmentLinkProps) {
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function open() {
    setFailed(false);
    setPending(true);
    const tab = window.open("", "_blank");
    if (tab) tab.opener = null;
    try {
      const url = await getAttachmentDownloadUrl(complaintId, attachmentId, { admin });
      if (tab) {
        tab.location.href = url;
      } else {
        window.location.assign(url);
      }
    } catch {
      tab?.close();
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <span>
      <button
        type="button"
        onClick={open}
        disabled={pending}
        className="underline underline-offset-4 disabled:opacity-60"
      >
        {label}
      </button>
      <span role="alert" className="ml-2 text-xs text-destructive">
        {failed ? errorText : null}
      </span>
    </span>
  );
}
