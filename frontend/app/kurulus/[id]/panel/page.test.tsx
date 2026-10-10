import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KurulusPanelPage from "./page";
import { useParams } from "next/navigation";
import { useSession } from "@/lib/session/use-session";
import {
  getOrganization,
  inviteOrgMember,
  listOrgMembers,
  updateMemberUnit,
  updateOrganization,
  verifyDomain,
  type OrgMember,
} from "@/lib/api/organizations";
import { transitionEngagement } from "@/lib/api/engagements";
import { apiFetch } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import type { PanelEngagement } from "./panel-data";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("@/lib/session/use-session");

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/lib/api/organizations", () => ({
  getOrganization: vi.fn(),
  inviteOrgMember: vi.fn(),
  verifyDomain: vi.fn(),
  listOrgMembers: vi.fn(),
  updateMemberUnit: vi.fn(),
  updateOrganization: vi.fn(),
}));

vi.mock("@/lib/api/engagements", () => ({
  transitionEngagement: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function sessionAs(role: "ADMIN" | "MEMBER" | null) {
  const organizations = role ? [{ id: "org-1", name: "Acme", role, unit: null }] : [{ id: "org-1", name: "Acme" }];
  return {
    data: { user: { id: "user-1", email: "admin@test.com" }, organizations, institutions: [], talent_profile: null },
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSession>;
}

const baseOrg = {
  id: "org-1",
  name: "Acme A.Ş.",
  domain: "acme.com",
  legal_id: "ORG-1",
  verification_level: "T1",
  status: "ACTIVE",
  showcase_public: false,
};

const members: OrgMember[] = [
  { user_id: "user-1", display_name: "Ayla Yönetici", role: "ADMIN", unit: null, open_assigned_count: 0, email: "a@acme.com" },
  { user_id: "user-2", display_name: "Mehmet Kaya", role: "MEMBER", unit: "Yazılım", open_assigned_count: 2, email: "m@acme.com" },
];

function engagement(id: string, status: string, extra: Partial<PanelEngagement> = {}): PanelEngagement {
  return {
    id,
    talent_id: `talent-${id}`,
    talent_name: `Kişi ${id}`,
    title: `Çalışma ${id}`,
    kind: "INTERNSHIP",
    status: status as PanelEngagement["status"],
    organization_id: "org-1",
    institution_id: null,
    organization_name: "Acme A.Ş.",
    version: 3,
    updated_at: "2026-10-01T10:00:00Z",
    ...extra,
  };
}

function withEngagements(items: PanelEngagement[]) {
  vi.mocked(apiFetch).mockResolvedValue({ items });
}

describe("KurulusPanelPage (/kurulus/[id]/panel)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "org-1" });
    vi.mocked(useSession).mockReturnValue(sessionAs("ADMIN"));
    vi.mocked(listOrgMembers).mockResolvedValue(members);
    withEngagements([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("happy path - organizasyon adı ve sicil no render edilir", async () => {
    vi.mocked(getOrganization).mockResolvedValueOnce(baseOrg);

    renderWithQueryClient(<KurulusPanelPage />);

    await waitFor(() => {
      expect(screen.getByText("Acme A.Ş.")).toBeTruthy();
      expect(screen.getByText("Ticari Sicil No: ORG-1")).toBeTruthy();
    });
  });

  it("404 - jenerik hata mesajı gösterilir", async () => {
    vi.mocked(getOrganization).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "Organizasyon bulunamadı.", requestId: null })
    );

    renderWithQueryClient(<KurulusPanelPage />);

    await waitFor(() => {
      expect(screen.getByText(/Organizasyon bulunamadı/i)).toBeTruthy();
    });
  });

  it("çalışmaları kuruluş filtresi ve 200 sınırıyla ister", async () => {
    vi.mocked(getOrganization).mockResolvedValue(baseOrg);

    renderWithQueryClient(<KurulusPanelPage />);

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/engagements?organization_id=org-1&limit=200"));
  });

  describe("Rol: yönetim kontrolleri (AC-1)", () => {
    it("ADMIN davet formunu, birim düzenlemeyi, vitrin anahtarını ve doğrulama düğmesini görür", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Mehmet Kaya")).toBeTruthy());
      expect(screen.getByLabelText("E-posta")).toBeTruthy();
      expect(screen.getByRole("switch", { name: "Vitrin herkese açık" })).toBeTruthy();
      expect(screen.getByRole("button", { name: "Mehmet Kaya için birimi düzenle" })).toBeTruthy();
      expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy();
      expect(screen.getByText("m@acme.com")).toBeTruthy();
    });

    it("MEMBER yönetim kontrollerini görmez, vitrini görebilir", async () => {
      vi.mocked(useSession).mockReturnValue(sessionAs("MEMBER"));
      vi.mocked(listOrgMembers).mockResolvedValue(members.map((m) => ({ ...m, email: null })));
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Mehmet Kaya")).toBeTruthy());
      expect(screen.queryByLabelText("E-posta")).toBeNull();
      expect(screen.queryByRole("switch")).toBeNull();
      expect(screen.queryByText("Birimi düzenle")).toBeNull();
      expect(screen.queryByText("Doğrulamayı Kontrol Et")).toBeNull();
      expect(screen.getByRole("link", { name: /Vitrini gör/ }).getAttribute("href")).toBe("/o/org-1");
    });

    it("rolü bilinmiyorsa (A öncesi /me) yönetim kontrolleri gizli kalır", async () => {
      vi.mocked(useSession).mockReturnValue(sessionAs(null));
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Mehmet Kaya")).toBeTruthy());
      expect(screen.queryByLabelText("E-posta")).toBeNull();
      expect(screen.queryByRole("switch")).toBeNull();
    });
  });

  describe("Alan adı doğrulama bölümü", () => {
    it("domain yoksa doğrulama yapılamaz mesajı gösterilir, buton yok", async () => {
      vi.mocked(getOrganization).mockResolvedValueOnce({ ...baseOrg, domain: null });

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => {
        expect(screen.getByText("Bu kuruluş için alan adı belirlenmemiş, doğrulama yapılamaz.")).toBeTruthy();
      });
      expect(screen.queryByText("Doğrulamayı Kontrol Et")).toBeNull();
    });

    it("domain T2+ ise küçük doğrulanmış rozeti gösterilir, buton yok", async () => {
      vi.mocked(getOrganization).mockResolvedValueOnce({ ...baseOrg, verification_level: "T2" });

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => {
        expect(screen.getByText(/Doğrulanmış alan adı/)).toBeTruthy();
      });
      expect(screen.queryByText("Doğrulamayı Kontrol Et")).toBeNull();
      expect(screen.queryByText("Alan Adı Doğrulama")).toBeNull();
    });

    it("kontrol edince pending dönerse TXT kaydı + pending mesajı gösterilir, buton Tekrar Dene'ye döner", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockResolvedValueOnce({ dns_txt_record: "yetkin360_verify_abc123", status: "pending" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(verifyDomain).toHaveBeenCalledWith("org-1");
        expect(screen.getByText("yetkin360_verify_abc123")).toBeTruthy();
        expect(screen.getByText(/Kayıt henüz bulunamadı/)).toBeTruthy();
        expect(screen.getByText("Tekrar Dene")).toBeTruthy();
      });
    });

    it("kontrol edince verified dönerse başarı mesajı gösterilir ve organizasyon yeniden çekilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockResolvedValueOnce({ dns_txt_record: "yetkin360_verify_abc123", status: "verified" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(screen.getByText("Alan adı doğrulandı.")).toBeTruthy();
      });
      await waitFor(() => {
        expect(vi.mocked(getOrganization)).toHaveBeenCalledTimes(2);
      });
    });

    it.each([
      ["FREE_EMAIL_DOMAIN", 400, /Ücretsiz e-posta sağlayıcıları/],
      ["TOO_MANY_REQUESTS", 429, /Çok sık deniyorsunuz/],
      ["DOMAIN_ALREADY_VERIFIED", 409, /başka bir kuruluşta zaten doğrulanmış/],
    ])("%s → ilgili hata mesajı gösterilir", async (code, status, text) => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(verifyDomain).mockRejectedValueOnce(new ApiError({ status, code, message: "x", requestId: null }));

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Doğrulamayı Kontrol Et")).toBeTruthy());
      await user.click(screen.getByText("Doğrulamayı Kontrol Et"));

      await waitFor(() => {
        expect(screen.getByText(text)).toBeTruthy();
      });
    });
  });

  describe("Üye davet bölümü", () => {
    it("happy path: birim boşsa birimsiz davet edilir, başarı mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(inviteOrgMember).mockResolvedValueOnce({ status: "queued" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "yeni-uye@test.com");
      await user.click(screen.getByText("Davet Gönder"));

      await waitFor(() => {
        expect(inviteOrgMember).toHaveBeenCalledWith("org-1", "yeni-uye@test.com", "MEMBER", undefined);
        expect(screen.getByText("Davet kuyruğa alındı.")).toBeTruthy();
      });
    });

    it("rol ve birim seçilirse onlarla çağrılır", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(inviteOrgMember).mockResolvedValueOnce({ status: "queued" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "yeni-admin@test.com");
      await user.selectOptions(screen.getByLabelText("Rol"), "ADMIN");
      await user.type(screen.getByLabelText("Birim (isteğe bağlı)"), " Ar-Ge ");
      await user.click(screen.getByText("Davet Gönder"));

      await waitFor(() => {
        expect(inviteOrgMember).toHaveBeenCalledWith("org-1", "yeni-admin@test.com", "ADMIN", "Ar-Ge");
      });
    });

    it("60 karakteri aşan birimde istek atılmaz, hata duyurulur", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "x@test.com");
      await user.type(screen.getByLabelText("Birim (isteğe bağlı)"), "x".repeat(61));
      await user.click(screen.getByText("Davet Gönder"));

      expect(await screen.findByText("Birim adı en fazla 60 karakter olabilir.")).toBeTruthy();
      expect(inviteOrgMember).not.toHaveBeenCalled();
    });

    it("davet başarısız olursa hata mesajı gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(inviteOrgMember).mockRejectedValueOnce(
        new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByLabelText("E-posta")).toBeTruthy());
      await user.type(screen.getByLabelText("E-posta"), "x@test.com");
      await user.click(screen.getByText("Davet Gönder"));

      await waitFor(() => {
        expect(screen.getByText("Davet gönderilemedi.")).toBeTruthy();
      });
    });
  });

  describe("Onay kutusu (AC-2, AC-3)", () => {
    it("bana atanan yoksa Tümü sekmesi açılır; başka kuruluşun kaydı listelenmez", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([
        engagement("a", "PENDING_EVALUATION"),
        engagement("x", "ACTIVE", { organization_id: "org-2" }),
      ]);

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Çalışma a")).toBeTruthy());
      expect(screen.getByRole("tab", { name: /Tümü/ }).getAttribute("aria-selected")).toBe("true");
      expect(screen.queryByText("Çalışma x")).toBeNull();
    });

    it("bana atanan varsa Bana atananlar varsayılan; yalnız onları gösterir, Tümü hepsini", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([
        engagement("mine", "PENDING_EVALUATION", { supervisor_user_id: "user-1" }),
        engagement("other", "PENDING_EVALUATION", { supervisor_user_id: "user-2" }),
      ]);

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Çalışma mine")).toBeTruthy());
      expect(screen.getByRole("tab", { name: /Bana atananlar/ }).getAttribute("aria-selected")).toBe("true");
      expect(screen.queryByText("Çalışma other")).toBeNull();

      await user.click(screen.getByRole("tab", { name: /Tümü/ }));
      expect(screen.getByText("Çalışma other")).toBeTruthy();
      // Onaylayıcı çipi ekip listesinden ad + birim
      expect(screen.getByText("Onaylayıcı: Mehmet Kaya · Yazılım")).toBeTruthy();
    });

    it("gruplar: aksiyon bekleyen, devam eden, tamamlanan (kapalı); reddedilen/iptal görünmez", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([
        engagement("pe", "PENDING_EVALUATION"),
        engagement("ac", "ACTIVE"),
        engagement("ve", "VERIFIED"),
        engagement("rj", "REJECTED"),
        engagement("cn", "CANCELLED"),
      ]);

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Çalışma pe")).toBeTruthy());
      const action = screen.getByRole("region", { name: /Sizden aksiyon bekleyen/ });
      expect(within(action).getByText("Çalışma pe")).toBeTruthy();
      const ongoing = screen.getByRole("region", { name: /^Devam eden/ });
      expect(within(ongoing).getByText("Çalışma ac")).toBeTruthy();
      expect(screen.queryByText("Çalışma ve")).toBeNull();
      expect(screen.queryByText("Çalışma rj")).toBeNull();
      expect(screen.queryByText("Çalışma cn")).toBeNull();

      await user.click(screen.getByRole("button", { name: "Tamamlananları göster (1)" }));
      expect(screen.getByText("Çalışma ve")).toBeTruthy();
    });

    it("PENDING_EVALUATION → Değerlendir bağlantısı", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([engagement("pe", "PENDING_EVALUATION")]);

      renderWithQueryClient(<KurulusPanelPage />);

      const link = await screen.findByRole("link", { name: "Değerlendir" });
      expect(link.getAttribute("href")).toBe("/calismalar/pe/degerlendirme");
    });

    it("ACTIVE → Değerlendirmeye al geçişi version ile gönderir ve listeyi yeniler", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([engagement("ac", "ACTIVE")]);
      vi.mocked(transitionEngagement).mockResolvedValueOnce({} as never);

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.click(await screen.findByRole("button", { name: "Değerlendirmeye al" }));

      await waitFor(() =>
        expect(transitionEngagement).toHaveBeenCalledWith("ac", { to_status: "PENDING_EVALUATION", version: 3 })
      );
      await waitFor(() => expect(vi.mocked(apiFetch).mock.calls.length).toBeGreaterThanOrEqual(2));
    });

    it("PRECONDITION_FAILED → 'Kişi henüz teslim eklemedi' duyurulur", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([engagement("ac", "ACTIVE")]);
      vi.mocked(transitionEngagement).mockRejectedValueOnce(
        new ApiError({ status: 422, code: "PRECONDITION_FAILED", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.click(await screen.findByRole("button", { name: "Değerlendirmeye al" }));

      const message = await screen.findByText("Kişi henüz teslim eklemedi.");
      expect(message.closest("[aria-live]")).toBeTruthy();
    });

    it("409 → liste yenilenir ve bilgi duyurulur", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([engagement("ac", "ACTIVE")]);
      vi.mocked(transitionEngagement).mockRejectedValueOnce(
        new ApiError({ status: 409, code: "VERSION_CONFLICT", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.click(await screen.findByRole("button", { name: "Değerlendirmeye al" }));

      expect(await screen.findByText("Kayıt bu arada değişti; liste yenilendi.")).toBeTruthy();
      await waitFor(() => expect(vi.mocked(apiFetch).mock.calls.length).toBeGreaterThanOrEqual(2));
    });

    it("EVALUATED + kurumsuz + ADMIN → Mühürle; kurumlu → bilgi çipi", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([
        engagement("solo", "EVALUATED"),
        engagement("uni", "EVALUATED", { institution_id: "inst-1", institution_name: "Galata Teknik Üniversitesi" }),
      ]);

      renderWithQueryClient(<KurulusPanelPage />);

      const seal = await screen.findByRole("link", { name: "Mühürle" });
      expect(seal.getAttribute("href")).toBe("/calismalar/solo#tanıklık");
      expect(screen.getByText("Üniversite mührü bekleniyor")).toBeTruthy();
      expect(screen.getAllByText("Galata Teknik Üniversitesi").length).toBeGreaterThan(0);
    });

    it("EVALUATED + kurumsuz + MEMBER → Mühürle yok", async () => {
      vi.mocked(useSession).mockReturnValue(sessionAs("MEMBER"));
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([engagement("solo", "EVALUATED")]);

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() => expect(screen.getByText("Çalışma solo")).toBeTruthy());
      expect(screen.queryByRole("link", { name: "Mühürle" })).toBeNull();
    });

    it("çalışma yoksa ne yapılacağını söyleyen boş durum gösterilir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      renderWithQueryClient(<KurulusPanelPage />);

      await waitFor(() =>
        expect(screen.getByText("Henüz bu kuruluşla yürütülen bir çalışma yok.")).toBeTruthy()
      );
      expect(screen.getAllByRole("button", { name: /Öğrenci bağlantısını kopyala/ }).length).toBeGreaterThan(0);
    });

    it("Tümünü gör /calismalar'a gider", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      renderWithQueryClient(<KurulusPanelPage />);

      expect((await screen.findByRole("link", { name: "Tümünü gör" })).getAttribute("href")).toBe("/calismalar");
    });
  });

  describe("İş birlikleri", () => {
    it("üniversite bazında kişi ve mühürlü sayısı; bireyseller ayrı satır", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      withEngagements([
        engagement("u1", "VERIFIED", { institution_id: "inst-1", institution_name: "Galata Teknik", talent_id: "t1" }),
        engagement("u2", "ACTIVE", { institution_id: "inst-1", institution_name: "Galata Teknik", talent_id: "t2" }),
        engagement("s1", "ACTIVE"),
      ]);

      renderWithQueryClient(<KurulusPanelPage />);

      const heading = await screen.findByRole("heading", { name: /İş birlikleri/ });
      const section = heading.closest("section") as HTMLElement;
      expect(within(section).getByText("Galata Teknik")).toBeTruthy();
      expect(within(section).getByText("2 kişi")).toBeTruthy();
      expect(within(section).getByText("1 mühürlü")).toBeTruthy();
      expect(within(section).getByText("Bireysel başvurular")).toBeTruthy();
    });
  });

  describe("Ekip ve birimler", () => {
    it("birime göre gruplar, açık atama sayısını gösterir", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);

      renderWithQueryClient(<KurulusPanelPage />);

      const unit = await screen.findByRole("region", { name: "Yazılım" });
      expect(within(unit).getByText("Mehmet Kaya")).toBeTruthy();
      expect(within(unit).getByText("2 açık atama")).toBeTruthy();
      expect(screen.getByRole("region", { name: "Birimi belirtilmemiş" })).toBeTruthy();
    });

    it("ADMIN satır içinde birim düzenler", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(updateMemberUnit).mockResolvedValueOnce({ ...members[1], unit: "Satış" });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.click(await screen.findByRole("button", { name: "Mehmet Kaya için birimi düzenle" }));
      const input = screen.getByLabelText("Birim");
      await user.clear(input);
      await user.type(input, "Satış");
      await user.click(screen.getByRole("button", { name: "Kaydet" }));

      await waitFor(() => expect(updateMemberUnit).toHaveBeenCalledWith("org-1", "user-2", "Satış"));
      await waitFor(() => expect(vi.mocked(listOrgMembers).mock.calls.length).toBeGreaterThanOrEqual(2));
    });

    it("birimi boşaltmak null gönderir; INVALID_UNIT duyurulur", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(updateMemberUnit).mockRejectedValueOnce(
        new ApiError({ status: 422, code: "INVALID_UNIT", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.click(await screen.findByRole("button", { name: "Mehmet Kaya için birimi düzenle" }));
      await user.clear(screen.getByLabelText("Birim"));
      await user.click(screen.getByRole("button", { name: "Kaydet" }));

      await waitFor(() => expect(updateMemberUnit).toHaveBeenCalledWith("org-1", "user-2", null));
      expect(await screen.findByText("Birim adı en fazla 60 karakter olabilir.")).toBeTruthy();
    });
  });

  describe("Vitrin", () => {
    it("ADMIN anahtarı açar; updateOrganization showcase_public ile çağrılır", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(updateOrganization).mockResolvedValueOnce({ ...baseOrg, showcase_public: true });

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      const toggle = await screen.findByRole("switch", { name: "Vitrin herkese açık" });
      expect(toggle.getAttribute("aria-checked")).toBe("false");
      await user.click(toggle);

      await waitFor(() => expect(updateOrganization).toHaveBeenCalledWith("org-1", { showcase_public: true }));
      await waitFor(() =>
        expect(screen.getByRole("switch", { name: "Vitrin herkese açık" }).getAttribute("aria-checked")).toBe("true")
      );
    });

    it("kaydedilemezse hata duyurulur", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      vi.mocked(updateOrganization).mockRejectedValueOnce(
        new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
      );

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.click(await screen.findByRole("switch", { name: "Vitrin herkese açık" }));

      expect(await screen.findByText("Vitrin ayarı kaydedilemedi.")).toBeTruthy();
    });
  });

  describe("Aday doğrula", () => {
    it("geçerli bağlantıda kendi origin'imizde yalnız yolu açar", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      const open = vi.spyOn(window, "open").mockReturnValue(null);

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.type(await screen.findByLabelText("Yetkin360 bağlantısı"), "https://kotu.example/v/abc_DEF-123");
      await user.click(screen.getByRole("button", { name: "Kaydı aç" }));

      expect(open).toHaveBeenCalledWith("/v/abc_DEF-123", "_blank", "noopener,noreferrer");
      open.mockRestore();
    });

    it("geçersiz bağlantıda hata duyurulur, hiçbir şey açılmaz", async () => {
      vi.mocked(getOrganization).mockResolvedValue(baseOrg);
      const open = vi.spyOn(window, "open").mockReturnValue(null);

      const user = userEvent.setup();
      renderWithQueryClient(<KurulusPanelPage />);

      await user.type(await screen.findByLabelText("Yetkin360 bağlantısı"), "javascript:alert(1)");
      await user.click(screen.getByRole("button", { name: "Kaydı aç" }));

      expect(await screen.findByText("Bu bir Yetkin360 doğrulama ya da profil bağlantısı değil.")).toBeTruthy();
      expect(open).not.toHaveBeenCalled();
      open.mockRestore();
    });
  });
});
