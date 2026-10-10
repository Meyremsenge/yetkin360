import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DeliverableForm } from "./deliverable-form";
import { createDeliverable } from "@/lib/api/deliverables";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";
import { makeViewer } from "@/lib/api/engagements.fixtures";

vi.mock("@/lib/api/deliverables", () => ({
  createDeliverable: vi.fn(),
}));

vi.mock("@/components/skill-picker", () => ({
  SkillPicker: ({ onChange, label }: { onChange: (id: string | null) => void; label: string }) => (
    <div>
      <span>{label}</span>
      <button type="button" onClick={() => onChange("skill-1")}>
        Mock Skill Seç
      </button>
    </div>
  ),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
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
  viewer: makeViewer({ relation: "SUBJECT", can_add_deliverable: true }),
};

describe("DeliverableForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("ACTIVE durumunda form render edilir", () => {
    renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    expect(screen.getByLabelText("Başlık")).toBeTruthy();
    expect(screen.getByText("Çıktı Ekle")).toBeTruthy();
  });

  it("viewer.can_add_deliverable false ise (ör. REJECTED) hiçbir şey render edilmez", () => {
    renderWithQueryClient(
      <DeliverableForm
        engagement={{ ...activeEngagement, status: "REJECTED", viewer: makeViewer({ relation: "SUBJECT" }) }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.queryByLabelText("Başlık")).toBeNull();
  });

  it("happy path: başlık girilip gönderilince createDeliverable çağrılır, başarı mesajı gösterilir, onSuccess tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createDeliverable).mockResolvedValueOnce({
      id: "deliv-1", engagement_id: "eng-1", skill_id: null, title: "Final Rapor",
      description: null, submitted_by_user_id: "user-1", submitted_at: "2026-10-04T00:00:00Z",
      created_at: "2026-10-04T00:00:00Z", updated_at: "2026-10-04T00:00:00Z",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Başlık"), "Final Rapor");
    await user.click(screen.getByText("Çıktı Ekle"));

    await waitFor(() => {
      expect(createDeliverable).toHaveBeenCalledWith("eng-1", { title: "Final Rapor", description: undefined, skill_id: undefined });
      expect(screen.getByText("Çıktı eklendi.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("skill seçilirse payload'a skill_id dahil edilir", async () => {
    vi.mocked(createDeliverable).mockResolvedValueOnce({
      id: "deliv-2", engagement_id: "eng-1", skill_id: "skill-1", title: "Kod",
      description: null, submitted_by_user_id: "user-1", submitted_at: "2026-10-04T00:00:00Z",
      created_at: "2026-10-04T00:00:00Z", updated_at: "2026-10-04T00:00:00Z",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "Kod");
    await user.click(screen.getByText("Mock Skill Seç"));
    await user.click(screen.getByText("Çıktı Ekle"));

    await waitFor(() => {
      expect(createDeliverable).toHaveBeenCalledWith("eng-1", { title: "Kod", description: undefined, skill_id: "skill-1" });
    });
  });

  it("403 FORBIDDEN → yetki hatası mesajı gösterilir", async () => {
    vi.mocked(createDeliverable).mockRejectedValueOnce(
      new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Çıktı Ekle"));

    await waitFor(() => {
      expect(screen.getByText("Bu işlemi yapma yetkiniz yok.")).toBeTruthy();
    });
  });

  it("422 PRECONDITION_FAILED → 'aktif değil' mesajı gösterilir ve onSuccess (refetch) tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createDeliverable).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "PRECONDITION_FAILED", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Çıktı Ekle"));

    await waitFor(() => {
      expect(screen.getByText("Çıktı yalnızca aktif çalışmalara eklenebilir.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("422 INVALID_REQUEST → geçersiz yetkinlik mesajı gösterilir", async () => {
    vi.mocked(createDeliverable).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "INVALID_REQUEST", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Çıktı Ekle"));

    await waitFor(() => {
      expect(screen.getByText("Seçilen yetkinlik geçersiz.")).toBeTruthy();
    });
  });

  it("başarı mesajı, durum ACTIVE'den çıksa bile bir an görünür kalır (early-return deseni)", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createDeliverable).mockResolvedValueOnce({
      id: "deliv-1", engagement_id: "eng-1", skill_id: null, title: "x",
      description: null, submitted_by_user_id: "user-1", submitted_at: "2026-10-04T00:00:00Z",
      created_at: "2026-10-04T00:00:00Z", updated_at: "2026-10-04T00:00:00Z",
    });

    const user = userEvent.setup();
    const { rerender } = renderWithQueryClient(<DeliverableForm engagement={activeEngagement} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Çıktı Ekle"));

    await waitFor(() => expect(screen.getByText("Çıktı eklendi.")).toBeTruthy());

    // Parent refetch sonrası durum artık PENDING_EVALUATION olsun — mesaj hâlâ görünür olmalı.
    rerender(
      <DeliverableForm
        engagement={{ ...activeEngagement, status: "PENDING_EVALUATION", viewer: makeViewer({ relation: "SUBJECT" }) }}
        onSuccess={onSuccess}
      />
    );
    expect(screen.getByText("Çıktı eklendi.")).toBeTruthy();
  });
});
