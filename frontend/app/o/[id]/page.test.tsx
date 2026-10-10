import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OrganizationShowcasePage from "@/app/o/[id]/page";
import { useParams } from "next/navigation";
import { getOrganizationShowcase, type OrganizationShowcase } from "@/lib/api/public";
import { ApiError, NetworkError } from "@/lib/api/errors";
import messages from "@/messages/tr.json";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));
vi.mock("@/lib/api/public", () => ({
  getOrganizationShowcase: vi.fn(),
}));

const t = messages.orgShowcase;

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <OrganizationShowcasePage />
    </QueryClientProvider>
  );
}

const openShowcase: OrganizationShowcase = {
  id: "org-1",
  name: "Lale Yazılım A.Ş.",
  verification_level: "T3",
  domain: "lale.com.tr",
  showcase_enabled: true,
  stats: { verified_public_count: 7, institution_count: 3 },
  experiences: [
    {
      role_snapshot: "Mobil Uygulama Stajı",
      started_on: "2026-07-01",
      ended_on: "2026-09-01",
      talent_display_name: "Ayşe Yılmaz",
      talent_public_slug: "ayse-yilmaz",
      institution_name: "Galata Teknik Üniversitesi",
      public_token: "tok-1",
      skills: ["React Native", "Test yazımı"],
    },
  ],
};

describe("OrganizationShowcasePage (/o/[id])", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "org-1" });
  });

  afterEach(() => {
    cleanup();
  });

  it("vitrin açıkken başlık, istatistik ve kayıt kartlarını gösterir", async () => {
    vi.mocked(getOrganizationShowcase).mockResolvedValueOnce(openShowcase);

    renderPage();

    expect(await screen.findByRole("heading", { level: 1, name: "Lale Yazılım A.Ş." })).toBeTruthy();
    expect(getOrganizationShowcase).toHaveBeenCalledWith("org-1");
    expect(screen.getByText("lale.com.tr")).toBeTruthy();
    expect(screen.getByText(t.domainVerified)).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Mobil Uygulama Stajı")).toBeTruthy();
    expect(screen.getByText("Galata Teknik Üniversitesi")).toBeTruthy();
    expect(screen.getByText("React Native")).toBeTruthy();
  });

  it("kişi profile, kayıt doğrulama sayfasına bağlanır", async () => {
    vi.mocked(getOrganizationShowcase).mockResolvedValueOnce(openShowcase);

    renderPage();

    const person = await screen.findByRole("link", { name: t.personLinkOf.replace("{name}", "Ayşe Yılmaz") });
    expect(person.getAttribute("href")).toBe("/p/ayse-yilmaz");
    const verify = screen.getByRole("link", {
      name: t.verifyRecordOf.replace("{role}", "Mobil Uygulama Stajı"),
    });
    expect(verify.getAttribute("href")).toBe("/v/tok-1");
  });

  it("vitrin kapalıysa kapalı durumunu gösterir, kayıt ve istatistik göstermez", async () => {
    vi.mocked(getOrganizationShowcase).mockResolvedValueOnce({
      ...openShowcase,
      showcase_enabled: false,
      stats: { verified_public_count: 0, institution_count: 0 },
      experiences: [],
    });

    renderPage();

    expect(await screen.findByText(t.closedTitle)).toBeTruthy();
    expect(screen.queryByText(t.recordsTitle)).toBeNull();
    expect(screen.queryByLabelText(t.statsLabel)).toBeNull();
  });

  it("vitrin açık ama kayıt yoksa boş durumu gösterir", async () => {
    vi.mocked(getOrganizationShowcase).mockResolvedValueOnce({
      ...openShowcase,
      stats: { verified_public_count: 0, institution_count: 0 },
      experiences: [],
    });

    renderPage();

    expect(await screen.findByText(t.emptyTitle)).toBeTruthy();
  });

  it("doğrulanmamış alan adını göstermez", async () => {
    vi.mocked(getOrganizationShowcase).mockResolvedValueOnce({ ...openShowcase, verification_level: "T1", domain: null });

    renderPage();

    await screen.findByRole("heading", { level: 1, name: "Lale Yazılım A.Ş." });
    expect(screen.queryByText(t.domainVerified)).toBeNull();
  });

  it("404 → bulunamadı durumu", async () => {
    vi.mocked(getOrganizationShowcase).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "ORGANIZATION_NOT_FOUND", message: "Kayıt bulunamadı", requestId: null })
    );

    renderPage();

    expect(await screen.findByText(t.notFound)).toBeTruthy();
  });

  it("ağ hatası → tekrar dene düğmesi", async () => {
    vi.mocked(getOrganizationShowcase).mockRejectedValueOnce(new NetworkError("network"));

    renderPage();

    expect(await screen.findByRole("button", { name: messages.publicVerification.retry })).toBeTruthy();
  });
});
