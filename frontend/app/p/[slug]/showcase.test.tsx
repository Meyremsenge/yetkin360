import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PublicProfilePage from "@/app/p/[slug]/page";
import { useParams } from "next/navigation";
import { getPublicProfile, type PublicProfile } from "@/lib/api/public";

vi.mock("next/navigation", () => ({ useParams: vi.fn() }));
vi.mock("@/lib/api/public", () => ({ getPublicProfile: vi.fn() }));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PublicProfilePage />
    </QueryClientProvider>
  );
}

const richProfile: PublicProfile = {
  display_name: "Ayşe Yılmaz",
  headline: "Backend geliştirmeye odaklı mühendislik öğrencisi",
  department: "Bilgisayar Mühendisliği",
  study_year: 4,
  city: "İstanbul",
  institution_name: "Galata Teknik Üniversitesi",
  institution_trust_level: "T3",
  attesting_organization_count: 2,
  skills: [
    { name_tr: "FastAPI", category: "FRAMEWORK", strength: "STRONG", attested: true, experience_count: 1 },
    { name_tr: "Python", category: "LANGUAGE", strength: "MODERATE", attested: false, experience_count: 2 },
  ],
  verified_experiences: [
    {
      id: "exp-1",
      organization_name_snapshot: "Lale Yazılım A.Ş.",
      organization_trust_level: "T3",
      role_snapshot: "Backend Geliştirme Stajı",
      institution_name_snapshot: "Galata Teknik Üniversitesi",
      started_on_snapshot: "2026-07-01",
      ended_on_snapshot: "2026-09-29",
      claim_type: "COMPETENCE",
      created_at: "2026-10-01T10:00:00Z",
      public_token: "tok-abc",
      skills: [{ name_tr: "FastAPI", category: "FRAMEWORK", claim_type: "COMPETENCE", attestor_organization: "Lale Yazılım A.Ş." }],
      evidenced_skills: [{ name_tr: "Python", category: "LANGUAGE" }],
    },
    {
      id: "exp-2",
      organization_name_snapshot: "Mavi Liman Lojistik",
      organization_trust_level: "T1",
      role_snapshot: "Depo Ekibi Raporlama Aracı",
      institution_name_snapshot: null,
      started_on_snapshot: "2025-11-01",
      ended_on_snapshot: "2025-11-22",
      claim_type: "PARTICIPATION",
      created_at: "2025-12-01T10:00:00Z",
      public_token: null,
      skills: [],
      evidenced_skills: [],
    },
  ],
};

describe("PublicProfilePage — vitrin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ slug: "ayse-yilmaz" });
  });
  afterEach(() => cleanup());

  it("hero: başlık, bölüm · sınıf · şehir ve doğrulanmış kurum gösterilir", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(richProfile);
    renderPage();

    await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Ayşe Yılmaz" })).toBeTruthy());
    expect(screen.getByText("Backend geliştirmeye odaklı mühendislik öğrencisi")).toBeTruthy();
    expect(screen.getByText("4. sınıf")).toBeTruthy();
    expect(screen.getByText("Doğrulanmış eğitim kurumu")).toBeTruthy();
  });

  it("güven şeridi gerçek sayıları gösterir", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(richProfile);
    renderPage();

    const strip = await screen.findByLabelText("Profil özeti");
    const values = within(strip).getAllByRole("definition").map((el) => el.textContent);
    expect(values).toEqual(["2", "2", "2"]);
  });

  it("yetkinlik haritası mühürlü ve yalnız kanıtlı yetkinlikleri ayırt eder", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(richProfile);
    renderPage();

    await screen.findByText("Yetkinlik haritası");
    expect(screen.getByText("Çatılar ve kütüphaneler")).toBeTruthy();
    expect(screen.getByText("Programlama dilleri")).toBeTruthy();
    expect(screen.getAllByText(/Mühürlü — bir kuruluş bu yetkinliğe tanıklık etti/).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Kanıtlı — görev veya çıktıda kullanıldı/).length).toBeGreaterThan(1);
  });

  it("deneyim kartı doğrulama linki ve T1 uyarısı taşır", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(richProfile);
    renderPage();

    const link = await screen.findByRole("link", { name: /Doğrulamayı gör/ });
    expect(link.getAttribute("href")).toBe("/v/tok-abc");
    // Only the record with a token gets a link.
    expect(screen.getAllByRole("link", { name: /Doğrulamayı gör/ })).toHaveLength(1);
    expect(screen.getByText("Kuruluş kimliği henüz doğrulanmadı")).toBeTruthy();
    expect(screen.getByText("Tanıklık eden: Lale Yazılım A.Ş.")).toBeTruthy();
    expect(screen.getByText("3 hafta")).toBeTruthy();
  });

  it("sicil kartında QR kod her zaman görünür ve profil adresini taşır", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce(richProfile);
    renderPage();

    const qr = await screen.findAllByRole("img", { name: "Ayşe Yılmaz profiline giden QR kod" });
    expect(qr.length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "QR kod" })).toBeNull();
    expect(screen.getAllByText(`${window.location.origin}/p/ayse-yilmaz`).length).toBeGreaterThan(0);
  });

  it("linki kopyala profil adresini panoya yazar", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    vi.mocked(getPublicProfile).mockResolvedValueOnce(richProfile);
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Linki kopyala" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/p/ayse-yilmaz`));
    expect(await screen.findByRole("button", { name: "Kopyalandı" })).toBeTruthy();
  });

  it("boş profilde güven şeridi ve harita gösterilmez, nazik boş durum çıkar", async () => {
    vi.mocked(getPublicProfile).mockResolvedValueOnce({
      display_name: "Ayşe Yılmaz",
      verified_experiences: [],
      skills: [],
      attesting_organization_count: 0,
    });
    renderPage();

    await screen.findByText("henüz doğrulanmış deneyim yok");
    expect(screen.queryByLabelText("Profil özeti")).toBeNull();
    expect(screen.queryByText("Yetkinlik haritası")).toBeNull();
  });
});
