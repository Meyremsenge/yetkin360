import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ComplaintSection } from "@/app/calismalar/[id]/complaint-section";
import { createComplaint, listEngagementComplaints, type Complaint } from "@/lib/api/complaints";
import type { EngagementDetail } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import { listEvidenceForDeliverable } from "@/lib/api/evidence";

vi.mock("@/lib/api/complaints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/complaints")>()),
  listEngagementComplaints: vi.fn(),
  createComplaint: vi.fn(),
}));
vi.mock("@/lib/api/evidence", () => ({ listEvidenceForDeliverable: vi.fn() }));

const STATEMENT = "Görevlerim üç haftadır onaylanmıyor, kuruluş yanıt vermiyor.";

const engagement: EngagementDetail = {
  id: "eng-1",
  title: "Backend Stajı",
  kind: "INTERNSHIP",
  status: "ACTIVE",
  organization_name: "Lale Yazılım A.Ş.",
  talent_id: "talent-1",
  organization_id: "org-1",
  institution_id: "inst-1",
  reason: null,
  version: 3,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-18T14:30:00Z",
  tasks: [],
  deliverables: [{ id: "del-1", title: "Sipariş servisi raporu", submitted_at: "2026-09-10T00:00:00Z" }],
  attestations: [],
};

function complaint(overrides: Partial<Complaint>): Complaint {
  return {
    id: "cmp-1",
    engagement_id: "eng-1",
    category: "TASK_APPROVAL",
    description: STATEMENT,
    evidence_id: null,
    status: "OPEN",
    decision_note: null,
    decided_at: null,
    created_at: "2026-10-01T00:00:00Z",
    ...overrides,
  };
}

function renderSection(target: EngagementDetail = engagement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ComplaintSection engagement={target} />
    </QueryClientProvider>,
  );
}

describe("ComplaintSection (öğrenci şikayeti)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listEngagementComplaints).mockResolvedValue([]);
    vi.mocked(listEvidenceForDeliverable).mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("şikayet yokken yalnız 'Şikayet oluştur' düğmesi görünür; form sonra açılır", async () => {
    const user = userEvent.setup();
    renderSection();

    expect(screen.queryByLabelText("Ne oldu?")).toBeNull();
    await user.click(await screen.findByRole("button", { name: "Şikayet oluştur" }));

    expect(screen.getByLabelText("Şikayet konusu")).toBeTruthy();
    expect(screen.getByLabelText("Ne oldu?").getAttribute("aria-required")).toBe("true");
    expect(screen.getByLabelText("Belge (isteğe bağlı)")).toBeTruthy();
  });

  it("kısa açıklama gönderilmez", async () => {
    const user = userEvent.setup();
    renderSection();

    await user.click(await screen.findByRole("button", { name: "Şikayet oluştur" }));
    await user.type(screen.getByLabelText("Ne oldu?"), "çok kısa");
    await user.click(screen.getByRole("button", { name: "Şikayeti gönder" }));

    expect(screen.getByRole("alert").textContent).toBe("Açıklama en az 20 karakter olmalı.");
    expect(createComplaint).not.toHaveBeenCalled();
  });

  it("konu ve açıklama ile şikayet gönderilir; sonra 'inceleniyor' durumu görünür", async () => {
    vi.mocked(createComplaint).mockResolvedValueOnce(complaint({ category: "PERSONAL" }));
    const user = userEvent.setup();
    renderSection();

    await user.click(await screen.findByRole("button", { name: "Şikayet oluştur" }));
    await user.selectOptions(screen.getByLabelText("Şikayet konusu"), "PERSONAL");
    await user.type(screen.getByLabelText("Ne oldu?"), STATEMENT);
    vi.mocked(listEngagementComplaints).mockResolvedValue([complaint({ category: "PERSONAL" })]);
    await user.click(screen.getByRole("button", { name: "Şikayeti gönder" }));

    await waitFor(() => {
      expect(createComplaint).toHaveBeenCalledWith("eng-1", { category: "PERSONAL", description: STATEMENT });
    });
    const open = await screen.findByTestId("complaint-open");
    expect(within(open).getByText("Şikayetiniz inceleniyor")).toBeTruthy();
    expect(within(open).getByText("Kişisel bir sorun yaşıyorum")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toBe("Şikayetiniz gönderildi.");
    expect(screen.queryByRole("button", { name: "Şikayet oluştur" })).toBeNull();
  });

  it("yalnız taraması tamamlanmış kanıtlar belge olarak seçilebilir ve seçilen gönderilir", async () => {
    vi.mocked(listEvidenceForDeliverable).mockResolvedValue([
      { id: "ev-clean", scan_status: "CLEAN", created_at: "2026-09-12T00:00:00Z" },
      { id: "ev-pending", scan_status: "PENDING", created_at: "2026-09-13T00:00:00Z" },
    ] as Awaited<ReturnType<typeof listEvidenceForDeliverable>>);
    vi.mocked(createComplaint).mockResolvedValueOnce(complaint({ evidence_id: "ev-clean" }));
    const user = userEvent.setup();
    renderSection();

    await user.click(await screen.findByRole("button", { name: "Şikayet oluştur" }));
    const select = screen.getByLabelText("Belge (isteğe bağlı)");
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(2));
    expect(within(select).getByRole("option", { name: /Sipariş servisi raporu/ })).toBeTruthy();

    await user.selectOptions(select, "ev-clean");
    await user.type(screen.getByLabelText("Ne oldu?"), STATEMENT);
    await user.click(screen.getByRole("button", { name: "Şikayeti gönder" }));

    await waitFor(() => {
      expect(createComplaint).toHaveBeenCalledWith("eng-1", {
        category: "TASK_APPROVAL",
        description: STATEMENT,
        evidence_id: "ev-clean",
      });
    });
  });

  it("eklenebilir kanıt yoksa belge alanı kapalıdır ve ne yapılacağı söylenir", async () => {
    const user = userEvent.setup();
    renderSection();

    await user.click(await screen.findByRole("button", { name: "Şikayet oluştur" }));

    expect((screen.getByLabelText("Belge (isteğe bağlı)") as HTMLSelectElement).disabled).toBe(true);
    expect(screen.getByText(/önce bir çıktıya kanıt yükleyin/)).toBeTruthy();
  });

  it("açık şikayet varken yeni şikayet formu sunulmaz", async () => {
    vi.mocked(listEngagementComplaints).mockResolvedValue([complaint({})]);
    renderSection();

    expect(await screen.findByTestId("complaint-open")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Şikayet oluştur" })).toBeNull();
  });

  it("karara bağlanan şikayet sonucu ve yönetici notuyla listelenir; yenisi açılabilir", async () => {
    vi.mocked(listEngagementComplaints).mockResolvedValue([
      complaint({ status: "UPHELD", decided_at: "2026-10-05T00:00:00Z", decision_note: "Kuruluş işlem yapmadı." }),
    ]);
    renderSection();

    const card = await screen.findByTestId("complaint-card");
    expect(within(card).getByText("Haklı bulundu")).toBeTruthy();
    expect(card.textContent).toContain("Kuruluş işlem yapmadı.");
    expect(screen.getByRole("button", { name: "Şikayet oluştur" })).toBeTruthy();
  });

  it("sunucu 'zaten açık şikayet var' derse bunu söyler", async () => {
    vi.mocked(createComplaint).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "COMPLAINT_ALREADY_OPEN", message: "x", requestId: null }),
    );
    const user = userEvent.setup();
    renderSection();

    await user.click(await screen.findByRole("button", { name: "Şikayet oluştur" }));
    await user.type(screen.getByLabelText("Ne oldu?"), STATEMENT);
    await user.click(screen.getByRole("button", { name: "Şikayeti gönder" }));

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toBe("Bu çalışma için zaten açık bir şikayetiniz var.");
    });
  });
});
