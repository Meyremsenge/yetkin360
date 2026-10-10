import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PortfolioSection from "@/app/profil/portfolio-section";
import {
  createPortfolioItem,
  deletePortfolioItem,
  listPortfolio,
  updatePortfolioItem,
  type PortfolioItem,
} from "@/lib/api/portfolio";
import { recordEvidence, requestUploadUrl, uploadFileToStorage } from "@/lib/api/evidence";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/lib/api/portfolio", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/portfolio")>()),
  listPortfolio: vi.fn(),
  createPortfolioItem: vi.fn(),
  updatePortfolioItem: vi.fn(),
  deletePortfolioItem: vi.fn(),
}));
vi.mock("@/lib/api/evidence", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/evidence")>()),
  requestUploadUrl: vi.fn(),
  uploadFileToStorage: vi.fn(),
  recordEvidence: vi.fn(),
}));

function item(overrides: Partial<PortfolioItem> = {}): PortfolioItem {
  return {
    id: "pi-1",
    kind: "CERTIFICATE",
    title: "Veri Analitiğine Giriş",
    issuer: "Coursera",
    issued_on: "2026-05-01",
    credential_id: "ABC123",
    external_url: null,
    evidence_id: null,
    show_on_profile: false,
    badge: "SELF_DECLARED",
    provider: null,
    created_at: "2026-10-01T10:00:00Z",
    ...overrides,
  };
}

function renderSection() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PortfolioSection />
    </QueryClientProvider>
  );
}

// The add form lives in a side sheet opened from the section header.
function openAddSheet() {
  fireEvent.click(screen.getByRole("button", { name: "Yeni kayıt" }));
}

describe("PortfolioSection — sertifikalar ve çalışmalar", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("boş durumda ne yapılacağını söyler", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    renderSection();
    expect(await screen.findByText("Henüz kayıt yok")).toBeInTheDocument();
    expect(screen.getByText(/Profilde göster/, { selector: "p" })).toBeInTheDocument();
  });

  it("kendi beyanı ile koordinatör onaylıyı farklı rozetlerle gösterir", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({
      items: [
        item({ id: "a", title: "Beyan", badge: "SELF_DECLARED" }),
        item({ id: "b", title: "Onaylı", badge: "COORDINATOR_CONFIRMED", evidence_id: "ev-1" }),
        item({ id: "c", title: "Reddedilen", badge: "COORDINATOR_REJECTED", evidence_id: "ev-2" }),
      ],
      engagement_certificates: [],
    });
    renderSection();
    const declared = (await screen.findByText("Beyan")).closest("li")!;
    const confirmed = screen.getByText("Onaylı").closest("li")!;
    expect(within(declared).getByText("Kendi beyanı")).toBeInTheDocument();
    expect(declared).toHaveClass("border-dashed");
    expect(within(confirmed).getAllByText("Koordinatör onaylı").length).toBeGreaterThan(0);
    expect(confirmed).not.toHaveClass("border-dashed");
    expect(screen.getByText(/profilde görünmez/)).toBeInTheDocument();
  });

  it("'Profilde göster' anahtarı rızayı sunucuya yollar", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [item()], engagement_certificates: [] });
    vi.mocked(updatePortfolioItem).mockResolvedValue(item({ show_on_profile: true }));
    renderSection();
    const toggle = await screen.findByRole("switch", { name: "Profilde göster" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    fireEvent.click(toggle);
    await waitFor(() => expect(updatePortfolioItem).toHaveBeenCalledWith("pi-1", { show_on_profile: true }));
  });

  it("kaydı kaldırır", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [item()], engagement_certificates: [] });
    vi.mocked(deletePortfolioItem).mockResolvedValue();
    renderSection();
    fireEvent.click(await screen.findByRole("button", { name: "Veri Analitiğine Giriş kaydını kaldır" }));
    await waitFor(() => expect(deletePortfolioItem).toHaveBeenCalledWith("pi-1"));
  });

  it("dosyasız yeni kayıt ekler; tarih ay başına çevrilir", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    vi.mocked(createPortfolioItem).mockResolvedValue(item());
    renderSection();
    await screen.findByText("Henüz kayıt yok");
    openAddSheet();

    fireEvent.click(screen.getByLabelText("Çalışma"));
    fireEvent.change(screen.getByLabelText("Başlık"), { target: { value: "Kişisel site" } });
    fireEvent.change(screen.getByLabelText("Tarih"), { target: { value: "2026-03" } });
    fireEvent.change(screen.getByLabelText("Bağlantı"), { target: { value: "https://ornek.dev" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() =>
      expect(createPortfolioItem).toHaveBeenCalledWith({
        kind: "WORK",
        title: "Kişisel site",
        issuer: null,
        issued_on: "2026-03-01",
        credential_id: null,
        external_url: "https://ornek.dev",
        evidence_id: null,
      })
    );
    expect(requestUploadUrl).not.toHaveBeenCalled();
  });

  it("http bağlantıyı ve boş başlığı reddeder, istek atmaz", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    renderSection();
    await screen.findByText("Henüz kayıt yok");
    openAddSheet();
    fireEvent.change(screen.getByLabelText("Bağlantı"), { target: { value: "http://ornek.dev" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    expect(await screen.findByText("Bağlantı https:// ile başlamalı.")).toBeInTheDocument();
    expect(screen.getByText("Başlık gerekli.")).toBeInTheDocument();
    expect(createPortfolioItem).not.toHaveBeenCalled();
  });

  it("dosya sürükle-bırak ile seçilir, güvenli akışla yüklenir ve kayda bağlanır", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    vi.mocked(requestUploadUrl).mockResolvedValue({ upload_url: "u", upload_fields: {}, object_key: "evidence/t/x.pdf", expires_in: 900 });
    vi.mocked(uploadFileToStorage).mockResolvedValue(undefined);
    vi.mocked(recordEvidence).mockResolvedValue({ id: "ev-9" } as Awaited<ReturnType<typeof recordEvidence>>);
    vi.mocked(createPortfolioItem).mockResolvedValue(item());
    renderSection();
    await screen.findByText("Henüz kayıt yok");
    openAddSheet();

    const file = new File(["%PDF"], "sertifika.pdf", { type: "application/pdf" });
    fireEvent.drop(screen.getByText("Dosyayı buraya bırak ya da seç").closest("label")!, { dataTransfer: { files: [file] } });
    expect(screen.getByText("Seçilen dosya: sertifika.pdf")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Başlık"), { target: { value: "SQL Temelleri" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() => expect(createPortfolioItem).toHaveBeenCalled());
    expect(recordEvidence).toHaveBeenCalledWith(expect.objectContaining({ kind: "CERTIFICATE", object_key: "evidence/t/x.pdf" }));
    expect(recordEvidence).toHaveBeenCalledWith(expect.not.objectContaining({ deliverable_id: expect.anything() }));
    expect(vi.mocked(createPortfolioItem).mock.calls[0][0].evidence_id).toBe("ev-9");
  });

  it("izinsiz dosya türünü sunucuya gitmeden reddeder", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    renderSection();
    await screen.findByText("Henüz kayıt yok");
    openAddSheet();
    const exe = new File(["MZ"], "kotu.exe", { type: "application/x-msdownload" });
    fireEvent.drop(screen.getByText("Dosyayı buraya bırak ya da seç").closest("label")!, { dataTransfer: { files: [exe] } });
    expect(await screen.findByText(/Desteklenmeyen dosya türü/)).toBeInTheDocument();
    expect(requestUploadUrl).not.toHaveBeenCalled();
  });

  it("50 kayıt sınırını anlaşılır mesajla bildirir", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    vi.mocked(createPortfolioItem).mockRejectedValue(
      new ApiError({ status: 409, code: "PORTFOLIO_LIMIT_REACHED", message: "x", requestId: null })
    );
    renderSection();
    await screen.findByText("Henüz kayıt yok");
    openAddSheet();
    fireEvent.change(screen.getByLabelText("Başlık"), { target: { value: "Fazla" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));
    expect(await screen.findByText("En fazla 50 kayıt ekleyebilirsin.")).toBeInTheDocument();
  });

  it("çalışmalardan gelen sertifikayı vitrine ekler; reddedileni ekletmez", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({
      items: [],
      engagement_certificates: [
        { evidence_id: "ev-1", created_at: "2026-09-01T00:00:00Z", provider: "COURSERA", credential_id: "C1", course_name: null, decision: "CONFIRMED", portfolio_item_id: null },
        { evidence_id: "ev-2", created_at: "2026-09-02T00:00:00Z", provider: "UDEMY", credential_id: null, course_name: null, decision: "REJECTED", portfolio_item_id: null },
      ],
    });
    vi.mocked(createPortfolioItem).mockResolvedValue(item());
    renderSection();
    const buttons = await screen.findAllByRole("button", { name: "Vitrine ekle" });
    expect(buttons[1]).toBeDisabled();
    fireEvent.click(buttons[0]);
    await waitFor(() =>
      expect(createPortfolioItem).toHaveBeenCalledWith({ kind: "CERTIFICATE", title: "Coursera sertifikası", evidence_id: "ev-1" })
    );
  });

  it("kurs adı varsa varsayılan başlık odur; BTK sağlayıcısı Türkçe etiketlenir", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({
      items: [],
      engagement_certificates: [
        { evidence_id: "ev-3", created_at: "2026-09-03T00:00:00Z", provider: "BTK", credential_id: "AbC123", course_name: "Siber Güvenliğe Giriş", decision: "CONFIRMED", portfolio_item_id: null },
        { evidence_id: "ev-4", created_at: "2026-09-04T00:00:00Z", provider: "UNKNOWN", credential_id: null, course_name: null, decision: null, portfolio_item_id: null },
      ],
    });
    vi.mocked(createPortfolioItem).mockResolvedValue(item());
    renderSection();
    expect(await screen.findByText("Siber Güvenliğe Giriş")).toBeInTheDocument();
    expect(screen.getByText("BTK Akademi")).toBeInTheDocument();

    const buttons = screen.getAllByRole("button", { name: "Vitrine ekle" });
    fireEvent.click(buttons[0]);
    await waitFor(() =>
      expect(createPortfolioItem).toHaveBeenCalledWith({ kind: "CERTIFICATE", title: "Siber Güvenliğe Giriş", evidence_id: "ev-3" })
    );
    fireEvent.click(buttons[1]);
    await waitFor(() =>
      expect(createPortfolioItem).toHaveBeenLastCalledWith({ kind: "CERTIFICATE", title: "Kurs sertifikası", evidence_id: "ev-4" })
    );
  });

  it("'Yeni kayıt' düğmesi formu sağdan açılan panelde açar; kapat düğmesi kapatır", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    const { container } = renderSection();
    await screen.findByText("Henüz kayıt yok");

    const dialog = container.querySelector("dialog")!;
    expect(dialog.hasAttribute("open")).toBe(false);
    const trigger = screen.getByRole("button", { name: "Yeni kayıt" });
    expect(trigger).toHaveAttribute("aria-haspopup", "dialog");

    openAddSheet();
    await waitFor(() => expect(dialog.hasAttribute("open")).toBe(true));
    expect(within(dialog).getByRole("heading", { name: "Yeni kayıt ekle" })).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Paneli kapat" }));
    await waitFor(() => expect(dialog.hasAttribute("open")).toBe(false));
  });

  it("başarılı kayıttan sonra panel kapanır", async () => {
    vi.mocked(listPortfolio).mockResolvedValue({ items: [], engagement_certificates: [] });
    vi.mocked(createPortfolioItem).mockResolvedValue(item());
    const { container } = renderSection();
    await screen.findByText("Henüz kayıt yok");
    openAddSheet();
    const dialog = container.querySelector("dialog")!;
    await waitFor(() => expect(dialog.hasAttribute("open")).toBe(true));

    fireEvent.change(screen.getByLabelText("Başlık"), { target: { value: "Kişisel site" } });
    fireEvent.click(screen.getByRole("button", { name: "Ekle" }));

    await waitFor(() => expect(createPortfolioItem).toHaveBeenCalled());
    await waitFor(() => expect(dialog.hasAttribute("open")).toBe(false));
  });
});
