import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EvidenceUploadForm } from "@/app/calismalar/[id]/evidence-upload-form";
import {
  requestUploadUrl,
  uploadFileToStorage,
  recordEvidence,
  listEvidenceForDeliverable,
} from "@/lib/api/evidence";
import type { EvidenceRecord } from "@/lib/api/evidence";

vi.mock("@/lib/api/evidence", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/evidence")>();
  return {
    ...actual,
    requestUploadUrl: vi.fn(),
    uploadFileToStorage: vi.fn(),
    recordEvidence: vi.fn(),
    listEvidenceForDeliverable: vi.fn(),
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

    render(<EvidenceUploadForm deliverableId="del-1" />);

    await waitFor(() => {
      expect(screen.getByText("Riskli — engellendi")).toBeTruthy();
    });
  });

  it("başlangıçta dosya girişini gösterir, henüz yüklenmiş kanıt yoktur", async () => {
    render(<EvidenceUploadForm deliverableId="del-1" />);

    await waitFor(() => {
      expect(listEvidenceForDeliverable).toHaveBeenCalledWith("del-1");
    });
    expect(screen.getByLabelText(/Kanıt dosyası ekle/)).toBeTruthy();
  });

  it("desteklenmeyen dosya türü seçilirse dosya reddi mesajı gösterilir, ağ çağrısı yapılmaz", async () => {
    const user = userEvent.setup();
    render(<EvidenceUploadForm deliverableId="del-1" />);

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
    render(<EvidenceUploadForm deliverableId="del-1" />);

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
    render(<EvidenceUploadForm deliverableId="del-1" />);

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
      expect(screen.getByText(/application\/pdf/)).toBeTruthy();
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
    render(<EvidenceUploadForm deliverableId="del-1" />);

    const input = screen.getByLabelText(/Kanıt dosyası ekle/) as HTMLInputElement;
    await user.upload(input, makeFile("rapor.pdf", "application/pdf"));

    await waitFor(() => {
      expect(screen.getByText("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.")).toBeTruthy();
    });
    expect(recordEvidence).not.toHaveBeenCalled();
  });
});
