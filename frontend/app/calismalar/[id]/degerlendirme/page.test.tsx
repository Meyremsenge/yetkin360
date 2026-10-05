import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DegerlendirmePage from "@/app/calismalar/[id]/degerlendirme/page";
import { useSession } from "@/lib/session/use-session";
import { useParams } from "next/navigation";
import { getEngagement } from "@/lib/api/engagements";
import type { EngagementDetail } from "@/lib/api/engagements";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));
vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/engagements", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/engagements")>();
  return { ...actual, getEngagement: vi.fn() };
});
vi.mock("@/app/calismalar/[id]/degerlendirme/evaluation-form", () => ({
  EvaluationForm: ({ onSubmitted }: { onSubmitted: () => void }) => (
    <div data-testid="evaluation-form">
      <button onClick={onSubmitted}>mock-submit</button>
    </div>
  ),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const pendingEvaluationEngagement: EngagementDetail = {
  id: "mock-eng-5",
  title: "Kısa Süreli Tasarım Danışmanlığı",
  kind: "SHORT_PROJECT",
  status: "PENDING_EVALUATION",
  organization_name: "Tasarım Atölyesi Ltd.",
  talent_id: "t-1",
  organization_id: "o-1",
  institution_id: null,
  reason: null,
  version: 3,
  created_at: "2026-08-20T00:00:00Z",
  updated_at: "2026-09-20T00:00:00Z",
  tasks: [],
  deliverables: [],
};

describe("DegerlendirmePage (/calismalar/[id]/degerlendirme)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "mock-eng-5" });
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: "user-1", email: "user@test.com" },
        organizations: [{ id: "org-1", name: "Test Org" }],
        institutions: [],
        talent_profile: null,
      },
      error: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
  });

  afterEach(() => {
    cleanup();
  });

  it("yüklenirken 'Yükleniyor...' gösterir", () => {
    vi.mocked(getEngagement).mockReturnValue(new Promise(() => {}));

    renderWithQueryClient(<DegerlendirmePage />);

    expect(screen.getByText("Yükleniyor...")).toBeTruthy();
  });

  it("engagement PENDING_EVALUATION değilse (örn. zaten değerlendirilmiş) form gösterilmez, uygun mesaj görünür", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce({
      ...pendingEvaluationEngagement,
      status: "EVALUATED",
    });

    renderWithQueryClient(<DegerlendirmePage />);

    await waitFor(() => {
      expect(
        screen.getByText("Bu çalışma değerlendirme aşamasında değil, form gösterilemiyor.")
      ).toBeTruthy();
      expect(screen.queryByTestId("evaluation-form")).toBeNull();
    });
  });

  it("PENDING_EVALUATION ise form gösterilir; gönderim sonrası başarı mesajına döner", async () => {
    vi.mocked(getEngagement).mockResolvedValueOnce(pendingEvaluationEngagement);

    renderWithQueryClient(<DegerlendirmePage />);

    await waitFor(() => {
      expect(screen.getByTestId("evaluation-form")).toBeTruthy();
    });

    screen.getByText("mock-submit").click();

    await waitFor(() => {
      expect(screen.getByText("Değerlendirme gönderildi.")).toBeTruthy();
    });
  });
});
