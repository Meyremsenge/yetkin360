"use client";

import { useState } from "react";
import {
  checkOrganizationDocument,
  rejectDocument,
  USE_MOCK_DOCUMENT_CHECK,
  type OrganizationDocumentCheckResult,
} from "@/lib/api/organization-document";
import messages from "@/messages/tr.json";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Kuruluş kaydında sicil/faaliyet belgesi adımı. Kontrol şu an mock'tur
 * (lib/api/organization-document.ts başlığına bakın): belge sunucuya gitmez,
 * sonuç kaydı ve doğrulama seviyesini etkilemez — bu yüzden form gönderimine
 * dahil değildir ve sonucun altında "örnek sonuç" notu gösterilir.
 */
export function OrganizationDocumentCheck({ entityName, legalId }: { entityName: string; legalId: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<OrganizationDocumentCheckResult | null>(null);

  const onFileChange = (selected: File | null) => {
    setResult(null);
    setFileError(null);
    if (!selected) {
      setFile(null);
      return;
    }
    const rejection = rejectDocument(selected);
    if (rejection) {
      setFile(null);
      setFileError(
        rejection === "INVALID_TYPE" ? messages.kayit.documentInvalidType : messages.kayit.documentTooLarge
      );
      return;
    }
    setFile(selected);
  };

  const onCheck = async () => {
    if (!file) return;
    setChecking(true);
    try {
      setResult(await checkOrganizationDocument(file, { entity_name: entityName, legal_id: legalId }));
    } catch {
      setFileError(messages.errors.generic);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div>
      <Label htmlFor="organization_document">{messages.kayit.documentLabel}</Label>
      <Input
        id="organization_document"
        type="file"
        accept="application/pdf,image/png,image/jpeg"
        aria-describedby="organization_document_hint"
        onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
      />
      <p id="organization_document_hint" className="text-xs text-muted-foreground mt-1">
        {messages.kayit.documentHint}
      </p>

      <Button type="button" variant="secondary" className="mt-2" disabled={!file || checking} onClick={onCheck}>
        {checking ? messages.kayit.documentChecking : messages.kayit.documentCheckButton}
      </Button>

      <div aria-live="polite">
        {fileError && <p className="text-xs text-red-600 mt-1">{fileError}</p>}

        {result && (
          <div
            className={
              result.status === "MATCH"
                ? "mt-2 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800"
                : "mt-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
            }
          >
            <p className="font-medium">
              {result.status === "MATCH" ? messages.kayit.documentMatch : messages.kayit.documentUnverified}
            </p>
            {result.qr_found && <p>{messages.kayit.documentQrFound}</p>}
            {result.status === "UNVERIFIED" && <p>{messages.kayit.documentNeedsClaim}</p>}
            {result.manual_review && <p>{messages.kayit.documentManualReview}</p>}
            {USE_MOCK_DOCUMENT_CHECK && <p className="mt-1 text-xs">{messages.kayit.documentDemoNote}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
