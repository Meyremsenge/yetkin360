import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TransitionActions } from "@/app/calismalar/[id]/transition-actions";
import { listApprovalRecipients, transitionEngagement } from "@/lib/api/engagements";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";
import { makeViewer } from "@/lib/api/engagements.fixtures";

vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return {
    ...actual,
    transitionEngagement: vi.fn(),
    listApprovalRecipients: vi.fn(),
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
  // Organization admin on an ACTIVE engagement (server-computed).
  supervisor: null,
  viewer: makeViewer({
    relation: "ORG_ADMIN",
    allowed_transitions: ["CANCELLED", "PENDING_EVALUATION"],
    reason_required: ["CANCELLED"],
  }),
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

  it("yalnız sunucunun izin verdiği geçişleri gösterir (durumdan tahmin etmez)", () => {
    renderWithQueryClient(
      <TransitionActions
        engagement={{
          ...activeEngagement,
          status: "DRAFT",
          institution_id: null,
          viewer: makeViewer({ relation: "SUBJECT", allowed_transitions: ["ACTIVE"] }),
        }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Onayla ve Aktifleştir")).toBeTruthy();
    expect(screen.queryByText("Onaya Gönder")).toBeNull();
  });

  it("SPRINT A: öğrenci onay bekleyen çalışmasında Onayla/Reddet düğmesini görmez", () => {
    renderWithQueryClient(
      <TransitionActions
        engagement={{
          ...activeEngagement,
          status: "PENDING_APPROVAL",
          institution_id: "inst-1",
          viewer: makeViewer({ relation: "SUBJECT" }),
        }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByText("Onayla ve Aktifleştir")).toBeNull();
    expect(screen.queryByText("Reddet")).toBeNull();
  });

  it("SPRINT A: koordinatör PENDING_APPROVAL'da Onayla ve Reddet görür; Reddet gerekçe ister", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <TransitionActions
        engagement={{
          ...activeEngagement,
          status: "PENDING_APPROVAL",
          institution_id: "inst-1",
          viewer: makeViewer({
            relation: "COORDINATOR",
            allowed_transitions: ["ACTIVE", "REJECTED"],
            reason_required: ["REJECTED"],
          }),
        }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Onayla ve Aktifleştir")).toBeTruthy();
    await user.click(screen.getByText("Reddet"));
    expect(screen.getByLabelText("Gerekçe")).toBeTruthy();
    expect(transitionEngagement).not.toHaveBeenCalled();
  });

  it("izin verilen geçiş yoksa (ör. terminal durum) hiçbir aksiyon gösterilmez", () => {
    renderWithQueryClient(
      <TransitionActions
        engagement={{ ...activeEngagement, status: "REJECTED", viewer: makeViewer({ relation: "ORG_ADMIN" }) }}
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
        engagement={{
          ...activeEngagement,
          status: "PENDING_EVALUATION",
          version: 3,
          viewer: makeViewer({ relation: "ORG_ADMIN" }),
        }}
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

  describe("onaya gönderirken koordinatör seçimi", () => {
    const draft: EngagementDetail = {
      ...activeEngagement,
      status: "DRAFT",
      institution_id: "inst-1",
      version: 1,
      viewer: makeViewer({ relation: "SUBJECT", allowed_transitions: ["PENDING_APPROVAL"] }),
    };
    const coordinators = [
      { user_id: "u-kerem", display_name: "Kerem Taşkın", email_hint: "ke•••@cinaralti.edu.test" },
      { user_id: "u-nermin", display_name: "Nermin Başaran", email_hint: "ne•••@cinaralti.edu.test" },
    ];
    const label = "Onay isteği kime gitsin?";

    function sent() {
      vi.mocked(transitionEngagement).mockResolvedValueOnce({ ...draft, status: "PENDING_APPROVAL", version: 2 });
    }

    it("'Onaya Gönder' hemen göndermez; okulun koordinatörlerini maskeli e-postayla listeler, varsayılan hepsidir", async () => {
      vi.mocked(listApprovalRecipients).mockResolvedValueOnce(coordinators);
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect(transitionEngagement).not.toHaveBeenCalled();
      const group = await screen.findByRole("group", { name: label });
      const radios = within(group).getAllByRole("radio") as HTMLInputElement[];
      expect(radios.map((radio) => radio.value)).toEqual(["", "u-kerem", "u-nermin"]);
      expect(radios[0].checked).toBe(true);
      expect(within(group).getByText("ke•••@cinaralti.edu.test")).toBeTruthy();
      // No free-text e-mail box any more.
      expect(screen.queryByRole("textbox")).toBeNull();
      expect(listApprovalRecipients).toHaveBeenCalledWith("eng-1");
      // One submit button only: the form replaces the action row.
      expect(screen.getAllByRole("button", { name: "Onaya Gönder" })).toHaveLength(1);
    });

    it("seçim yapılmazsa alıcısız gönderilir ve tüm koordinatörlere gittiği söylenir", async () => {
      vi.mocked(listApprovalRecipients).mockResolvedValueOnce(coordinators);
      sent();
      const onSuccess = vi.fn();
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={onSuccess} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await screen.findByRole("group", { name: label });
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      await waitFor(() => {
        expect(transitionEngagement).toHaveBeenCalledWith("eng-1", {
          to_status: "PENDING_APPROVAL",
          version: 1,
          reason: undefined,
        });
        expect(onSuccess).toHaveBeenCalled();
        expect(screen.getByRole("status").textContent).toBe(
          "Onay isteği okulunuzun koordinatörlerine gönderildi."
        );
      });
    });

    it("seçilen koordinatör notify_user_ids olarak gönderilir ve adıyla bildirilir", async () => {
      vi.mocked(listApprovalRecipients).mockResolvedValueOnce(coordinators);
      sent();
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await user.click(await screen.findByRole("radio", { name: /Nermin Başaran/ }));
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      await waitFor(() => {
        expect(transitionEngagement).toHaveBeenCalledWith(
          "eng-1",
          expect.objectContaining({ to_status: "PENDING_APPROVAL", notify_user_ids: ["u-nermin"] })
        );
        expect(screen.getByRole("status").textContent).toBe(
          "Onay isteği Nermin Başaran adlı koordinatöre gönderildi."
        );
      });
    });

    it("liste boşsa ya da alınamazsa seçim gösterilmez, istek yine tüm koordinatörlere gönderilebilir", async () => {
      vi.mocked(listApprovalRecipients).mockRejectedValueOnce(
        new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
      );
      sent();
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect(await screen.findByText("Onay isteği okulunuzun koordinatörlerine gider.")).toBeTruthy();
      expect(screen.queryAllByRole("radio")).toHaveLength(0);
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await waitFor(() => {
        expect(vi.mocked(transitionEngagement).mock.calls[0][1].notify_user_ids).toBeUndefined();
      });
    });

    it("okulsuz çalışmada (PRECONDITION_FAILED) okula bağlanması gerektiği söylenir", async () => {
      vi.mocked(listApprovalRecipients).mockResolvedValueOnce([]);
      vi.mocked(transitionEngagement).mockRejectedValueOnce(
        new ApiError({ status: 422, code: "PRECONDITION_FAILED", message: "x", requestId: null })
      );
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await screen.findByText("Onay isteği okulunuzun koordinatörlerine gider.");
      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));

      expect((await screen.findByRole("alert")).textContent).toBe(
        "Bu çalışma bir okula bağlı olmadığı için onaya gönderilemiyor. Önce profilinizden okulunuza bağlanın."
      );
    });

    it("'Vazgeç' kutuyu kapatır ve hiçbir şey göndermez", async () => {
      vi.mocked(listApprovalRecipients).mockResolvedValueOnce(coordinators);
      const user = userEvent.setup();
      renderWithQueryClient(<TransitionActions engagement={draft} onSuccess={vi.fn()} />);

      await user.click(screen.getByRole("button", { name: "Onaya Gönder" }));
      await screen.findByRole("group", { name: label });
      await user.click(screen.getByRole("button", { name: "Vazgeç" }));

      expect(screen.queryByRole("group", { name: label })).toBeNull();
      expect(screen.getByRole("button", { name: "Onaya Gönder" })).toBeTruthy();
      expect(transitionEngagement).not.toHaveBeenCalled();
    });
  });
});
