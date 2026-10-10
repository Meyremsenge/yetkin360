import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KesfetPage from "@/app/kesfet/page";
import { listSkills } from "@/lib/api/client";
import { listDiscoverOrganizations, listDiscoverTalents } from "@/lib/api/discover";
import { ApiError } from "@/lib/api/errors";
import { useSession } from "@/lib/session/use-session";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/discover", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/discover")>()),
  listDiscoverTalents: vi.fn(),
  listDiscoverOrganizations: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({ listSkills: vi.fn() }));
vi.mock("@/lib/session/use-session");

const t = messages.kesfet;

const alice = {
  public_slug: "alice-slug",
  full_name: "Alice Yılmaz",
  headline: "Backend geliştirici",
  department: "Bilgisayar Mühendisliği",
  city: "İstanbul",
  institution_name: "Bilgi Üniversitesi",
  sealed_skills: ["Python", "SQL"],
  verified_experience_count: 2,
};
const bora = {
  public_slug: "bora-slug",
  full_name: "Bora Kaya",
  headline: null,
  department: null,
  city: null,
  institution_name: null,
  sealed_skills: [],
  verified_experience_count: 0,
};
const acme = { id: "org-1", name: "Acme A.Ş.", verification_level: "T2", domain: "acme.com" };

function page<T>(items: T[], next_cursor: string | null = null) {
  return { items, next_cursor, has_more: next_cursor !== null };
}

function mockSession(talentProfile: object | null) {
  vi.mocked(useSession).mockReturnValue({
    data: {
      user: { id: "user-1", email: "user@test.com" },
      organizations: [],
      institutions: [],
      talent_profile: talentProfile,
    },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>);
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <KesfetPage />
    </QueryClientProvider>
  );
}

describe("KesfetPage (/kesfet)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSession(null);
    vi.mocked(listDiscoverTalents).mockResolvedValue(page([alice, bora]));
    vi.mocked(listDiscoverOrganizations).mockResolvedValue(page([acme]));
    vi.mocked(listSkills).mockResolvedValue({ items: [] });
  });

  afterEach(() => {
    cleanup();
  });

  describe("Öğrenciler sekmesi", () => {
    it("yüklenirken yükleme durumu gösterir", () => {
      vi.mocked(listDiscoverTalents).mockReturnValue(new Promise(() => {}));
      renderPage();
      expect(screen.getByRole("status", { name: t.talentsLoading })).toBeTruthy();
    });

    it("kartta ad, başlık, mühürlü yetkinlikler, deneyim sayısı ve public profil linki var", async () => {
      renderPage();
      const heading = await screen.findByRole("heading", { name: "Alice Yılmaz" });
      const card = heading.closest("article") as HTMLElement;

      expect(within(card).getByText("Backend geliştirici")).toBeTruthy();
      expect(within(card).getByText("Bilgi Üniversitesi · Bilgisayar Mühendisliği · İstanbul")).toBeTruthy();
      const chips = within(within(card).getByRole("list", { name: t.sealedSkillsLabel })).getAllByRole("listitem");
      expect(chips.map((chip) => chip.textContent)).toEqual(["Python", "SQL"]);
      expect(within(card).getByText("2 doğrulanmış deneyim")).toBeTruthy();
      expect(
        within(card).getByRole("link", { name: "Alice Yılmaz profilini gör" }).getAttribute("href")
      ).toBe("/p/alice-slug");
    });

    it("mühürlü yetkinliği olmayan kartta bunu açıkça söyler", async () => {
      renderPage();
      const card = (await screen.findByRole("heading", { name: "Bora Kaya" })).closest("article") as HTMLElement;
      expect(within(card).getByText(t.noSealedSkills)).toBeTruthy();
      expect(within(card).getByText("0 doğrulanmış deneyim")).toBeTruthy();
    });

    it("kartlar giriş animasyonu sınıfını taşır", async () => {
      renderPage();
      const card = (await screen.findByRole("heading", { name: "Alice Yılmaz" })).closest("li") as HTMLElement;
      expect(card.className).toContain("y360-step-in");
    });

    it("hiç öğrenci yoksa ne yapılacağını söyleyen boş durum gösterir", async () => {
      vi.mocked(listDiscoverTalents).mockResolvedValue(page([]));
      renderPage();
      expect(await screen.findByText(t.talentsEmptyTitle)).toBeTruthy();
      expect(screen.getByText(t.talentsEmptyBody)).toBeTruthy();
      expect(screen.queryByRole("button", { name: t.clearFilters })).toBeNull();
    });

    it("hata verirse mesaj ve tekrar dene butonu gösterir, tekrar dener", async () => {
      vi.mocked(listDiscoverTalents).mockRejectedValueOnce(new Error("network fail"));
      renderPage();
      const alert = await screen.findByRole("alert");
      expect(within(alert).getByText(t.talentsError)).toBeTruthy();

      fireEvent.click(within(alert).getByRole("button", { name: t.retry }));
      expect(await screen.findByRole("heading", { name: "Alice Yılmaz" })).toBeTruthy();
    });

    it("429'da hız sınırı mesajı gösterir", async () => {
      vi.mocked(listDiscoverTalents).mockRejectedValueOnce(
        new ApiError({ status: 429, code: "RATE_LIMITED", message: "x", requestId: null })
      );
      renderPage();
      expect(await screen.findByText(t.rateLimited)).toBeTruthy();
    });

    it("arama metnini gecikmeli olarak q filtresine çevirir", async () => {
      renderPage();
      await screen.findByRole("heading", { name: "Alice Yılmaz" });
      fireEvent.change(screen.getByRole("searchbox", { name: t.talentSearchLabel }), {
        target: { value: "alice" },
      });
      await waitFor(() =>
        expect(vi.mocked(listDiscoverTalents)).toHaveBeenLastCalledWith(expect.objectContaining({ q: "alice" }))
      );
    });

    it("2 karakterden kısa aramayı filtre saymaz", async () => {
      renderPage();
      await screen.findByRole("heading", { name: "Alice Yılmaz" });
      fireEvent.change(screen.getByRole("searchbox", { name: t.talentSearchLabel }), { target: { value: "a" } });
      await new Promise((resolve) => setTimeout(resolve, 400));
      expect(vi.mocked(listDiscoverTalents)).toHaveBeenCalledTimes(1);
    });

    it("bölüm filtresi çip olarak görünür; boş sonuçta filtreler temizlenebilir", async () => {
      renderPage();
      await screen.findByRole("heading", { name: "Alice Yılmaz" });
      vi.mocked(listDiscoverTalents).mockResolvedValue(page([]));

      fireEvent.change(screen.getByLabelText(t.departmentLabel), { target: { value: "Hukuk" } });
      await waitFor(() =>
        expect(vi.mocked(listDiscoverTalents)).toHaveBeenLastCalledWith(
          expect.objectContaining({ department: "Hukuk" })
        )
      );
      expect(screen.getByRole("button", { name: "Bölüm: Hukuk filtresini kaldır" })).toBeTruthy();
      expect(await screen.findByText(t.talentsEmptyFilteredTitle)).toBeTruthy();

      vi.mocked(listDiscoverTalents).mockResolvedValue(page([alice]));
      fireEvent.click(screen.getAllByRole("button", { name: t.clearFilters })[0]);
      expect(await screen.findByRole("heading", { name: "Alice Yılmaz" })).toBeTruthy();
      expect((screen.getByLabelText(t.departmentLabel) as HTMLInputElement).value).toBe("");
    });

    it("yetkinlik önerisine tıklanınca skill_id filtresi eklenir ve çip görünür", async () => {
      vi.mocked(listSkills).mockResolvedValue({ items: [{ id: "skill-1", name_tr: "Python" }] });
      renderPage();
      await screen.findByRole("heading", { name: "Alice Yılmaz" });

      fireEvent.change(screen.getByLabelText(t.skillLabel), { target: { value: "pyt" } });
      fireEvent.click(await screen.findByRole("button", { name: "+ Python" }));

      await waitFor(() =>
        expect(vi.mocked(listDiscoverTalents)).toHaveBeenLastCalledWith(
          expect.objectContaining({ skillIds: ["skill-1"] })
        )
      );
      expect(screen.getByRole("button", { name: "Python filtresini kaldır" })).toBeTruthy();
    });

    it("daha fazla göster sonraki sayfayı imleçle ister ve listeye ekler", async () => {
      vi.mocked(listDiscoverTalents)
        .mockResolvedValueOnce(page([alice], "cursor-1"))
        .mockResolvedValueOnce(page([bora]));
      renderPage();
      await screen.findByRole("heading", { name: "Alice Yılmaz" });

      fireEvent.click(screen.getByRole("button", { name: t.loadMore }));

      expect(await screen.findByRole("heading", { name: "Bora Kaya" })).toBeTruthy();
      expect(screen.getByRole("heading", { name: "Alice Yılmaz" })).toBeTruthy();
      expect(vi.mocked(listDiscoverTalents)).toHaveBeenLastCalledWith(
        expect.objectContaining({ cursor: "cursor-1" })
      );
      expect(screen.queryByRole("button", { name: t.loadMore })).toBeNull();
    });
  });

  describe("Kuruluşlar sekmesi", () => {
    async function openOrganizations() {
      renderPage();
      fireEvent.click(screen.getByRole("tab", { name: t.tabOrganizations }));
      return (await screen.findByRole("heading", { name: "Acme A.Ş." })).closest("article") as HTMLElement;
    }

    it("sekme değişince kuruluş kartlarını gösterir", async () => {
      const card = await openOrganizations();
      expect(screen.getByRole("tab", { name: t.tabOrganizations }).getAttribute("aria-selected")).toBe("true");
      expect(within(card).getByText("acme.com")).toBeTruthy();
      expect(within(card).getByText(messages.kurulusSec.verificationLevel.T2)).toBeTruthy();
    });

    it("öğrenci profili olmayan kullanıcıya çalışma başlat linki göstermez", async () => {
      const card = await openOrganizations();
      expect(within(card).queryByRole("link")).toBeNull();
    });

    it("öğrenciye çalışma başlat linki mevcut oluşturma akışına gider", async () => {
      mockSession({ id: "talent-1" });
      const card = await openOrganizations();
      expect(
        within(card).getByRole("link", { name: "Acme A.Ş. ile çalışma başlat" }).getAttribute("href")
      ).toBe("/calismalar/olustur?organization_id=org-1");
    });

    it("kuruluş yoksa boş durum gösterir", async () => {
      vi.mocked(listDiscoverOrganizations).mockResolvedValue(page([]));
      renderPage();
      fireEvent.click(screen.getByRole("tab", { name: t.tabOrganizations }));
      expect(await screen.findByText(t.organizationsEmptyTitle)).toBeTruthy();
    });
  });
});
