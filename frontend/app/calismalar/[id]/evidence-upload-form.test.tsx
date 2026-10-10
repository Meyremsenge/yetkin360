import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EvidenceUploadForm } from "@/app/calismalar/[id]/evidence-upload-form";
import {
  requestUploadUrl,
  uploadFileToStorage,
  recordEvidence,
  listEvidenceForDeliverable,
  listCertificateChecksForEngagement,
  requestCertificateCheck,
} from "@/lib/api/evidence";
import { ApiError } from "@/lib/api/errors";
import type { EvidenceRecord, CertificateCheck } from "@/lib/api/evidence";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/evidence", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/evidence")>();
  return {
    ...actual,
    requestUploadUrl: vi.fn(),
    uploadFileToStorage: vi.fn(),
    recordEvidence: vi.fn(),
    listEvidenceForDeliverable: vi.fn(),
    requestCertificateCheck: vi.fn(),
    listCertificateChecksForEngagement: vi.fn(),
  };
});

function makeFile(name: string, type: string, sizeBytes = 1024): File {
  return new File([new Uint8Array(sizeBytes)], name, { type });
}

const mockRecord: EvidenceRecord = {
  id: "mock-evidence-1",
  deliverable_id: "del-1",
  kind: "DOCUMENT",
  provenance: "SELF_UPLOADED",
  object_key: "evidence/mock/x.pdf",
  mime_type: "application/pdf",
  size_bytes: 2048,
  scan_status: "PENDING",
  created_at: "2026-09-24T00:00:00Z",
};

/**
 * YET-98/99 (PLAN 2.12): 3 adımlı kanıt yükleme akışı + ilerleme/hata gösterimi.
 */
describe("EvidenceUploadForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listEvidenceForDeliverable).mockResolvedValue([]);
    vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("scan_status=INFECTED olan bir kanıt kırmızı 'Riskli — engellendi' rozetiyle gösterilir", async () => {
    // Mock tarama simülasyonu artık deterministik olarak hep CLEAN'e dönüyor (bkz.
    // lib/api/evidence.ts — kullanıcı geri bildirimi üzerine rastgelelik kaldırıldı),
    // bu yüzden INFECTED render'ı burada sabit veriyle doğrulanıyor.
    vi.mocked(listEvidenceForDeliverable).mockResolvedValue([
      { ...mockRecord, scan_status: "INFECTED" },
    ]);

    render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

    await waitFor(() => {
      expect(screen.getByText("Riskli — engellendi")).toBeTruthy();
    });
  });

  it("başlangıçta dosya girişini gösterir, henüz yüklenmiş kanıt yoktur", async () => {
    render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

    await waitFor(() => {
      expect(listEvidenceForDeliverable).toHaveBeenCalledWith("del-1");
    });
    expect(screen.getByLabelText(/Kanıt dosyası ekle/)).toBeTruthy();
  });

  it("desteklenmeyen dosya türü seçilirse dosya reddi mesajı gösterilir, ağ çağrısı yapılmaz", async () => {
    const user = userEvent.setup();
    render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

    // Dosya adı ".pdf" olsa da gerçek MIME türü değil — kontrolümüz uzantıya değil
    // browser'ın bildirdiği content-type'a bakıyor (uzantı spoofing'ine karşı doğru davranış).
    const input = screen.getByLabelText(/Kanıt dosyası ekle/) as HTMLInputElement;
    await user.upload(input, makeFile("virus.pdf", "application/x-msdownload"));

    await waitFor(() => {
      expect(
        screen.getByText("Desteklenmeyen dosya türü. İzin verilen türler: PDF, JPEG, PNG, DOCX.")
      ).toBeTruthy();
    });
    expect(requestUploadUrl).not.toHaveBeenCalled();
  });

  it("10MB üstü dosya seçilirse dosya reddi mesajı gösterilir, ağ çağrısı yapılmaz", async () => {
    const user = userEvent.setup();
    render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

    const input = screen.getByLabelText(/Kanıt dosyası ekle/) as HTMLInputElement;
    await user.upload(input, makeFile("buyuk.pdf", "application/pdf", 11 * 1024 * 1024));

    await waitFor(() => {
      expect(screen.getByText(/Dosya çok büyük/)).toBeTruthy();
    });
    expect(requestUploadUrl).not.toHaveBeenCalled();
  });

  it("geçerli dosya seçilince 3 adım sırayla çağrılır ve yeni kanıt listede görünür", async () => {
    vi.mocked(requestUploadUrl).mockResolvedValueOnce({
      upload_url: "https://mock/upload",
      upload_fields: { key: "evidence/mock/x.pdf" },
      object_key: "evidence/mock/x.pdf",
      expires_in: 900,
    });
    vi.mocked(uploadFileToStorage).mockResolvedValueOnce(undefined);
    vi.mocked(recordEvidence).mockResolvedValueOnce(mockRecord);
    vi.mocked(listEvidenceForDeliverable)
      .mockResolvedValueOnce([]) // mount
      .mockResolvedValueOnce([mockRecord]); // upload sonrası refresh

    const user = userEvent.setup();
    render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

    const input = screen.getByLabelText(/Kanıt dosyası ekle/) as HTMLInputElement;
    await user.upload(input, makeFile("rapor.pdf", "application/pdf"));

    await waitFor(() => {
      expect(requestUploadUrl).toHaveBeenCalledTimes(1);
      expect(uploadFileToStorage).toHaveBeenCalledWith(
        "https://mock/upload",
        { key: "evidence/mock/x.pdf" },
        expect.objectContaining({ name: "rapor.pdf" })
      );
      expect(recordEvidence).toHaveBeenCalledWith({
        deliverable_id: "del-1",
        object_key: "evidence/mock/x.pdf",
        kind: "DOCUMENT",
        mime_type: "application/pdf",
        size_bytes: 1024,
      });
    });

    await waitFor(() => {
      expect(screen.getByText("Taranıyor")).toBeTruthy();
      // The file type is shown as a short chip ("pdf"), not the raw MIME type.
      expect(screen.getByText("pdf")).toBeTruthy();
    });
  });

  it("adımlardan biri hata verirse genel hata mesajı gösterilir", async () => {
    vi.mocked(requestUploadUrl).mockResolvedValueOnce({
      upload_url: "https://mock/upload",
      upload_fields: {},
      object_key: "evidence/mock/x.pdf",
      expires_in: 900,
    });
    vi.mocked(uploadFileToStorage).mockRejectedValueOnce(new Error("depolama hatası"));

    const user = userEvent.setup();
    render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

    const input = screen.getByLabelText(/Kanıt dosyası ekle/) as HTMLInputElement;
    await user.upload(input, makeFile("rapor.pdf", "application/pdf"));

    await waitFor(() => {
      expect(screen.getByText(messages.errors.generic)).toBeTruthy();
    });
    expect(recordEvidence).not.toHaveBeenCalled();
  });

  describe("tarama sonucu için yeniden okuma (YET-195)", () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it("PENDING kayıt varken liste periyodik yeniden okunur", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      vi.mocked(listEvidenceForDeliverable).mockResolvedValue([mockRecord]);

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);
      await waitFor(() => expect(listEvidenceForDeliverable).toHaveBeenCalledTimes(1));

      await vi.advanceTimersByTimeAsync(3100);

      expect(vi.mocked(listEvidenceForDeliverable).mock.calls.length).toBeGreaterThan(1);
    });

    it("bekleyen kayıt yoksa (CLEAN/FAILED) yeniden okuma yapılmaz", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      vi.mocked(listEvidenceForDeliverable).mockResolvedValue([{ ...mockRecord, scan_status: "CLEAN" }]);

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);
      await waitFor(() => expect(listEvidenceForDeliverable).toHaveBeenCalledTimes(1));

      await vi.advanceTimersByTimeAsync(9000);

      expect(listEvidenceForDeliverable).toHaveBeenCalledTimes(1);
    });
  });

  describe("PLAN 3.55: sertifika kontrolü", () => {
    const mockCertificateRecord: EvidenceRecord = {
      ...mockRecord,
      kind: "CERTIFICATE",
      scan_status: "CLEAN",
    };

    it("sertifika kutusu işaretlenince rıza metni gösterilir", async () => {
      const user = userEvent.setup();
      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

      const checkbox = await screen.findByLabelText(messages.calismalar.certificateCheckboxLabel);
      await user.click(checkbox);

      expect(screen.getByText(messages.calismalar.certificateCheckConsentHint)).toBeTruthy();
    });

    it("sertifika yüklenirken kind=CERTIFICATE ile kaydedilir (kutu işaretliyken)", async () => {
      const user = userEvent.setup();
      vi.mocked(requestUploadUrl).mockResolvedValue({
        upload_url: "https://storage.test/upload",
        upload_fields: {},
        object_key: "evidence/mock/x.png",
        expires_in: 900,
      });
      vi.mocked(uploadFileToStorage).mockResolvedValue(undefined);
      vi.mocked(recordEvidence).mockResolvedValue(mockCertificateRecord);

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);
      await user.click(await screen.findByLabelText(messages.calismalar.certificateCheckboxLabel));

      const file = makeFile("sertifika.png", "image/png");
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      await user.upload(input, file);

      await waitFor(() => {
        expect(recordEvidence).toHaveBeenCalledWith(
          expect.objectContaining({ kind: "CERTIFICATE" })
        );
      });
    });

    it("CLEAN sertifika için 'AI ile kontrol iste' butonu gösterilir ve tıklanınca talep gönderilir", async () => {
      const user = userEvent.setup();
      vi.mocked(listEvidenceForDeliverable).mockResolvedValue([mockCertificateRecord]);
      const createdCheck: CertificateCheck = {
        id: "check-1",
        evidence_id: mockCertificateRecord.id,
        status: "PENDING",
        provider: null,
        credential_id: null,
        verify_url: null,
        qr_raw_data: null,
        extracted_name: null,
        name_match: null,
        page_name: null,
        page_match: null,
        decision: "PENDING",
        decided_by_user_id: null,
        decided_at: null,
        created_at: "2026-10-10T00:00:00Z",
      };
      vi.mocked(requestCertificateCheck).mockResolvedValue(createdCheck);

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

      const button = await screen.findByText(messages.calismalar.certificateCheckRequestButton);
      await user.click(button);

      await waitFor(() => {
        expect(requestCertificateCheck).toHaveBeenCalledWith(mockCertificateRecord.id);
      });
      await waitFor(() => {
        expect(screen.getByText(messages.calismalar.certificateCheckStatus.PENDING)).toBeTruthy();
      });
    });

    it("tamamlanmış kontrol sonucu (provider, kimlik no, isim eşleşmesi, doğrulama linki) gösterilir", async () => {
      vi.mocked(listEvidenceForDeliverable).mockResolvedValue([mockCertificateRecord]);
      vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
        {
          id: "check-1",
          evidence_id: mockCertificateRecord.id,
          status: "DONE",
          provider: "UDEMY",
          credential_id: "UC-123",
          verify_url: "https://udemy.com/cert/UC-123",
          qr_raw_data: null,
          extracted_name: "Ahmet Yılmaz",
          name_match: true,
          page_name: null,
          page_match: null,
          decision: "PENDING",
          decided_by_user_id: null,
          decided_at: null,
          created_at: "2026-10-10T00:00:00Z",
        },
      ]);

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

      await waitFor(() => {
        expect(screen.getByText(/UC-123/)).toBeTruthy();
      });
      expect(screen.getByText(/Ahmet Yılmaz/)).toBeTruthy();
      expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckNameMatchYes))).toBeTruthy();
      expect(screen.getByText(messages.calismalar.certificateCheckVerifyLinkLabel)).toBeTruthy();
      expect(screen.getByText(messages.calismalar.certificateCheckDecisionPending)).toBeTruthy();
    });

    it("resmi sayfa karşılaştırması (page_name/page_match) varsa gösterilir", async () => {
      vi.mocked(listEvidenceForDeliverable).mockResolvedValue([mockCertificateRecord]);
      vi.mocked(listCertificateChecksForEngagement).mockResolvedValue([
        {
          id: "check-1",
          evidence_id: mockCertificateRecord.id,
          status: "DONE",
          provider: "COURSERA",
          credential_id: "ABC123",
          verify_url: "https://coursera.org/verify/ABC123",
          qr_raw_data: null,
          extracted_name: "Ahmet Yılmaz",
          name_match: true,
          page_name: "Ahmet Yılmaz",
          page_match: true,
          decision: "PENDING",
          decided_by_user_id: null,
          decided_at: null,
          created_at: "2026-10-10T00:00:00Z",
        },
      ]);

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);

      await waitFor(() => {
        expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckPageNameLabel))).toBeTruthy();
      });
      expect(screen.getByText(new RegExp(messages.calismalar.certificateCheckPageMatchYes))).toBeTruthy();
    });

    it("409 ALREADY_REQUESTED hatasında uyarı mesajı gösterilir", async () => {
      const user = userEvent.setup();
      vi.mocked(listEvidenceForDeliverable).mockResolvedValue([mockCertificateRecord]);
      vi.mocked(requestCertificateCheck).mockRejectedValue(
        new ApiError({ status: 409, code: "ALREADY_REQUESTED", message: "x", requestId: null })
      );

      render(<EvidenceUploadForm deliverableId="del-1" engagementId="eng-1" />);
      const button = await screen.findByText(messages.calismalar.certificateCheckRequestButton);
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(messages.calismalar.certificateCheckAlreadyRequested)).toBeTruthy();
      });
    });
  });
});
