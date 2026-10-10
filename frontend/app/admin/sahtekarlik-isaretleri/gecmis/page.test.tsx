import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SahtekarlikGecmisiPage from "@/app/admin/sahtekarlik-isaretleri/gecmis/page";
import { useSession } from "@/lib/session/use-session";
import { ApiError } from "@/lib/api/errors";
import * as auditApi from "@/lib/api/admin-audit";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin-audit", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/admin-audit")>();
  return { ...actual, getFraudHistory: vi.fn() };
});

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <SahtekarlikGecmisiPage />
    </QueryClientProvider>
  );
}

const flag = {
  id: "f1",
  subject_type: "ORGANIZATION",
  subject_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  subject_label: null,
  signal: null,
  reason: "Kural gerekçesi",
  confidence: "HIGH" as const,
  model: "rules-v1",
  status: "CONFIRMED" as const,
  created_at: "2026-10-01T10:00:00Z",
  reviewed_at: null,
  reviewed_by_user_id: null,
};

describe("SahtekarlikGecmisiPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: "admin-1", email: "a@test.com", is_platform_admin: true },
        organizations: [],
        institutions: [],
        talent_profile: null,
      },
      error: null,
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);
  });
  afterEach(cleanup);

  it("renders reviewed flag with null-safe reviewer fields", async () => {
    vi.mocked(auditApi.getFraudHistory).mockResolvedValue({
      items: [flag],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    await waitFor(() => expect(screen.getByText("Kural gerekçesi")).toBeTruthy());
    expect(screen.getAllByText("Onaylandı").length).toBeGreaterThanOrEqual(2);
    expect(document.body.textContent).not.toContain("null");
    expect(document.body.textContent).not.toContain("Invalid Date");
  });

  it("shows empty state pointing back to the queue", async () => {
    vi.mocked(auditApi.getFraudHistory).mockResolvedValue({
      items: [],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/karara bağlanmış işaret yok/)).toBeTruthy());
  });

  it("shows error alert on failure", async () => {
    vi.mocked(auditApi.getFraudHistory).mockRejectedValue(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
    );
    renderPage();
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
  });

  it("status filter requests DISMISSED from offset 0", async () => {
    vi.mocked(auditApi.getFraudHistory).mockResolvedValue({
      items: [flag],
      limit: 50,
      offset: 0,
      has_more: false,
    });
    renderPage();
    await screen.findByText("Kural gerekçesi");
    await userEvent.selectOptions(screen.getByLabelText("Karar"), "DISMISSED");
    await waitFor(() =>
      expect(auditApi.getFraudHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "DISMISSED", offset: 0 })
      )
    );
  });
});
