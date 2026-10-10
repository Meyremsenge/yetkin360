import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KurumlarPage from "@/app/admin/kurumlar/page";
import { useSession } from "@/lib/session/use-session";
import { ApiError } from "@/lib/api/errors";
import * as dir from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin-directory", async (orig) => {
  const actual = await orig<typeof import("@/lib/api/admin-directory")>();
  return { ...actual, listInstitutions: vi.fn(), setSuspended: vi.fn(), setInstitutionVerificationLevel: vi.fn() };
});

const m = messages.adminInstitutions;
const inst: dir.AdminInstitution = {
  id: "i1", name: "Örnek Üniversitesi", domain: null, verification_level: "T1",
  status: "ACTIVE", created_at: "2026-09-20T00:00:00Z",
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <KurumlarPage />
    </QueryClientProvider>
  );
}

describe("KurumlarPage (/admin/kurumlar)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: { user: { id: "admin", email: "admin@example.com", is_platform_admin: true }, organizations: [], institutions: [], talent_profile: null },
      error: null,
      isError: false,
      refetch: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useSession>);
    vi.mocked(dir.listInstitutions).mockResolvedValue({ items: [inst], limit: 50, offset: 0, has_more: false });
  });
  afterEach(cleanup);

  it("renders the institution with a null domain as —", async () => {
    renderPage();
    await screen.findByText("Örnek Üniversitesi");
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("saves a new verification level", async () => {
    vi.mocked(dir.setInstitutionVerificationLevel).mockResolvedValue({ ...inst, verification_level: "T3" });
    renderPage();
    const select = await screen.findByLabelText(`${m.levelLabel}: Örnek Üniversitesi`);
    const save = screen.getByRole("button", { name: m.saveLevel });
    expect(save).toBeDisabled();
    await userEvent.selectOptions(select, "T3");
    await userEvent.click(save);
    await waitFor(() => expect(dir.setInstitutionVerificationLevel).toHaveBeenCalledWith("i1", "T3"));
    expect(await screen.findByText(m.levelUpdated)).toBeInTheDocument();
  });

  it("shows not-found when the institution disappeared", async () => {
    vi.mocked(dir.setInstitutionVerificationLevel).mockRejectedValue(
      new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null })
    );
    renderPage();
    await userEvent.selectOptions(await screen.findByLabelText(`${m.levelLabel}: Örnek Üniversitesi`), "T2");
    await userEvent.click(screen.getByRole("button", { name: m.saveLevel }));
    expect(await screen.findByText(m.notFound)).toBeInTheDocument();
  });
});
