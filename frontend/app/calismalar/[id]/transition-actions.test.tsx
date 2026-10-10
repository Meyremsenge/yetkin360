import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TransitionActions } from "@/app/calismalar/[id]/transition-actions";
import { transitionEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";

vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return {
    ...actual,
    transitionEngagement: vi.fn(),
  };
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  // `wrapper` kullanılıyor ki `rerender(...)` çağrıları da aynı Provider'ı korusun.
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return render(ui, { wrapper: Wrapper });
}

const activeEngagement: EngagementDetail = {
  id: "eng-1",
  title: "Yaz Kısa Projesi",
  kind: "SHORT_PROJECT",
  status: "ACTIVE",
  organization_name: "Bulut Sistemleri Ltd.",
  talent_id: "talent-1",
  organization_id: "org-1",
  institution_id: null,
  reason: null,
  version: 2,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-18T14:30:00Z",
  tasks: [],
  deliverables: [],
  attestations: [],
};

/**
 * YET-97 (PLAN 2.11): Durum geçiş aksiyonları — POST /transitions bağlantısı + hata gösterimi (409/422/403).
 */
describe("TransitionActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("ACTIVE durumu için aday geçiş butonlarını gösterir", () => {
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={vi.fn()} />
    );

    expect(screen.getByText("İptal Et")).toBeTruthy();
    expect(screen.getByText("Değerlendirmeye Gönder")).toBeTruthy();
  });

  it("DRAFT + institution_id=null (doğrudan kuruluş engagement'ı) için ACTIVE gösterilir, PENDING_APPROVAL değil", () => {
    // Canlı bulgu: bu durumda eskiden 'Onaya Gönder' gösteriliyordu ama backend
    // institution_id_not_null ön koşulu yüzünden her zaman 422 PRECONDITION_FAILED
    // dönüyordu (app/services/engagement.py:313-316) — kullanıcı hiçbir zaman
    // çalışmasını aktifleştiremiyordu.
    renderWithQueryClient(
      <TransitionActions
        engagement={{ ...activeEngagement, status: "DRAFT", institution_id: null }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Onayla ve Aktifleştir")).toBeTruthy();
    expect(screen.queryByText("Onaya Gönder")).toBeNull();
  });

  it("DRAFT + institution_id dolu (kurum bağlantılı engagement) için PENDING_APPROVAL gösterilir", () => {
    renderWithQueryClient(
      <TransitionActions
        engagement={{ ...activeEngagement, status: "DRAFT", institution_id: "inst-1" }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Onaya Gönder")).toBeTruthy();
  });

  it("terminal durumda (REJECTED) hiçbir aksiyon gösterilmez", () => {
    renderWithQueryClient(
      <TransitionActions
        engagement={{ ...activeEngagement, status: "REJECTED" }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.queryByRole("button")).toBeNull();
  });

  it("gerekçe gerektirmeyen geçiş (PENDING_EVALUATION) direkt çağrılır ve başarı mesajı gösterilir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(transitionEngagement).mockResolvedValueOnce({
      ...activeEngagement,
      status: "PENDING_EVALUATION",
      version: 3,
    });

    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={onSuccess} />
    );

    await user.click(screen.getByText("Değerlendirmeye Gönder"));

    await waitFor(() => {
      expect(transitionEngagement).toHaveBeenCalledWith("eng-1", {
        to_status: "PENDING_EVALUATION",
        version: 2,
        reason: undefined,
      });
      expect(onSuccess).toHaveBeenCalled();
      expect(screen.getByText("Durum güncellendi.")).toBeTruthy();
    });
  });

  it("gerekçe gereken geçişte (CANCELLED) önce gerekçe alanı gösterilir, boşsa gönderilmez", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={vi.fn()} />
    );

    await user.click(screen.getByText("İptal Et"));

    expect(screen.getByLabelText("Gerekçe")).toBeTruthy();

    await user.click(screen.getByText("Uygula"));

    expect(transitionEngagement).not.toHaveBeenCalled();
    expect(screen.getByText("Bu işlem için gerekçe girilmesi zorunludur.")).toBeTruthy();
  });

  it("gerekçe girilip gönderilince transitionEngagement doğru payload ile çağrılır", async () => {
    vi.mocked(transitionEngagement).mockResolvedValueOnce({
      ...activeEngagement,
      status: "CANCELLED",
      version: 3,
      reason: "Proje sonlandırıldı.",
    });

    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={vi.fn()} />
    );

    await user.click(screen.getByText("İptal Et"));
    await user.type(screen.getByLabelText("Gerekçe"), "Proje sonlandırıldı.");
    await user.click(screen.getByText("Uygula"));

    await waitFor(() => {
      expect(transitionEngagement).toHaveBeenCalledWith("eng-1", {
        to_status: "CANCELLED",
        version: 2,
        reason: "Proje sonlandırıldı.",
      });
    });
  });

  it("409 CONFLICT hatasında uyarı gösterilir ve onSuccess (refetch) tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(transitionEngagement).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "CONFLICT", message: "conflict", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={onSuccess} />
    );

    await user.click(screen.getByText("Değerlendirmeye Gönder"));

    await waitFor(() => {
      expect(
        screen.getByText("Kayıt başka bir işlemle değişti, güncel durum yeniden yüklendi.")
      ).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("403 FORBIDDEN hatasında yetkisiz mesajı gösterilir, onSuccess ÇAĞRILMAZ", async () => {
    const onSuccess = vi.fn();
    vi.mocked(transitionEngagement).mockRejectedValueOnce(
      new ApiError({ status: 403, code: "FORBIDDEN", message: "forbidden", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={onSuccess} />
    );

    await user.click(screen.getByText("Değerlendirmeye Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bu işlemi yapma yetkiniz yok.")).toBeTruthy();
    });
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("REGRESYON: 409 hatası sonrası parent refetch ile terminal duruma geçse de hata mesajı kaybolmaz", async () => {
    // Manuel test bulgusu: parent, onSuccess() ile refetch tetikleyip engagement'ı terminal
    // bir duruma (candidates=[]) güncellediğinde, component eskiden koşulsuz `return null`
    // yapıp az önce gösterdiği formError'ı hemen siliyordu — kullanıcı mesajı okuyamıyordu.
    const onSuccess = vi.fn();
    vi.mocked(transitionEngagement).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "CONFLICT", message: "conflict", requestId: null })
    );

    const user = userEvent.setup();
    const { rerender } = renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={onSuccess} />
    );

    await user.click(screen.getByText("Değerlendirmeye Gönder"));

    await waitFor(() => {
      expect(
        screen.getByText("Kayıt başka bir işlemle değişti, güncel durum yeniden yüklendi.")
      ).toBeTruthy();
    });

    // Parent'ın refetch sonrası verdiği yeni prop: engagement artık terminal bir durumda
    // (candidates boş) — gerçek page.tsx'te bu, queryClient.invalidateQueries sonrası olur.
    rerender(
      <TransitionActions
        engagement={{ ...activeEngagement, status: "PENDING_EVALUATION", version: 3 }}
        onSuccess={onSuccess}
      />
    );

    expect(
      screen.getByText("Kayıt başka bir işlemle değişti, güncel durum yeniden yüklendi.")
    ).toBeTruthy();
  });

  it("422 ILLEGAL_TRANSITION hatasında uyarı gösterilir ve onSuccess (refetch) tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(transitionEngagement).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "ILLEGAL_TRANSITION", message: "illegal", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions engagement={activeEngagement} onSuccess={onSuccess} />
    );

    await user.click(screen.getByText("Değerlendirmeye Gönder"));

    await waitFor(() => {
      expect(
        screen.getByText("Bu durumda bu işlem yapılamaz, güncel durum yeniden yüklendi.")
      ).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  describe("onaya gönderirken alıcı seçimi", () => {
    const draft: EngagementDetail = { ...activeEngagement, status: "DRAFT", institution_id: "inst-1", version: 1 };

    function sent() {
      vi.mocked(transitionEngagement).mockResolvedValueOnce({ ...draft, status: "PENDING_APPROVAL", version: 2 });
    }

    it("'Onaya Gönder' hemen göndermez; önce zorunlu alıcı kutusunu açar", async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect(transitionEngagement).not.toHaveBeenCalled();
      const input = screen.getByLabelText("Onay isteği kime gitsin?");
      expect(input.getAttribute("aria-required")).toBe("true");
      // One submit button only: the form replaces the action row.
      expect(screen.getAllByRole("button", { name: "Onaya Gönder" })).toHaveLength(1);
    });

    it("kutu boşsa istek gönderilmez ve alıcının zorunlu olduğu söylenir", async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect(screen.getByRole("alert").textContent).toBe("Onay isteğinin gideceği en az bir e-posta adresi yazın.");
      expect(transitionEngagement).not.toHaveBeenCalled();
    });

    it("yazılan adresler notify_emails olarak gönderilir ve ne olacağı açıklanır", async () => {
      sent();
      const onSuccess = vi.fn();
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={onSuccess} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await user.type(
        screen.getByLabelText("Onay isteği kime gitsin?"),
        "kerem@kurum.edu.tr, selin@kurum.edu.tr",
      );
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      await waitFor(() => {
        expect(transitionEngagement).toHaveBeenCalledWith("eng-1", {
          to_status: "PENDING_APPROVAL",
          version: 1,
          reason: undefined,
          notify_emails: ["kerem@kurum.edu.tr", "selin@kurum.edu.tr"],
        });
        expect(onSuccess).toHaveBeenCalled();
        expect(screen.getByRole("status").textContent).toContain("kurumun kayıtlı koordinatörüne aitse");
      });
    });

    it("biçimi bozuk adres gönderilmez, hata adresi adıyla bildirir", async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await user.type(screen.getByLabelText("Onay isteği kime gitsin?"), "koordinator");
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect(screen.getByRole("alert").textContent).toBe("Geçerli bir e-posta adresi değil: koordinator");
      expect(transitionEngagement).not.toHaveBeenCalled();
    });

    it("beşten fazla adres gönderilmez", async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await user.type(
        screen.getByLabelText("Onay isteği kime gitsin?"),
        "a@k.tr b@k.tr c@k.tr d@k.tr e@k.tr f@k.tr",
      );
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect(screen.getByRole("alert").textContent).toBe("En fazla 5 adres yazabilirsiniz.");
      expect(transitionEngagement).not.toHaveBeenCalled();
    });

    it("'Vazgeç' kutuyu kapatır ve hiçbir şey göndermez", async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await user.click(screen.getByRole("button", { name: "Vazgeç" }));

      expect(screen.queryByLabelText("Onay isteği kime gitsin?")).toBeNull();
      expect(screen.getByRole("button", { name: "Onaya Gönder" })).toBeTruthy();
      expect(transitionEngagement).not.toHaveBeenCalled();
    });
  });
});
