import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KuruluslarPage from "@/app/admin/kuruluslar/page";
import { useSession } from "@/lib/session/use-session";
import * as dir from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin-directory", async (orig) => {
  const actual = await orig<typeof import("@/lib/api/admin-directory")>();
  return { ...actual, listOrganizations: vi.fn(), setSuspended: vi.fn() };
});

const m = messages.adminOrganizations;

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <KuruluslarPage />
    </QueryClientProvider>
  );
}

describe("KuruluslarPage (/admin/kuruluslar)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: { user: { id: "admin", email: "admin@example.com", is_platform_admin: true }, organizations: [], institutions: [], talent_profile: null },
      error: null,
      isError: false,
      refetch: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useSession>);
  });
  afterEach(cleanup);

  it("renders null fields as — and Doğrulanmadı, never 'null' or Invalid Date", async () => {
    vi.mocked(dir.listOrganizations).mockResolvedValue({
      items: [
        {
          id: "o1", name: "Boş Ltd.", legal_id: null, domain: null, verification_level: "T1",
          verified_at: null, status: "ACTIVE", created_at: "2026-09-20T00:00:00Z",
        },
      ],
      limit: 50, offset: 0, has_more: false,
    });
    renderPage();
    await screen.findByText("Boş Ltd.");
    expect(screen.getAllByText("—").length).toBe(2);
    expect(screen.getByText(m.notVerified)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/null|Invalid Date/);
  });

  it("filters by verification level", async () => {
    vi.mocked(dir.listOrganizations).mockResolvedValue({ items: [], limit: 50, offset: 0, has_more: false });
    renderPage();
    await screen.findByText(m.empty);
    await userEvent.selectOptions(screen.getByLabelText(m.filterLevel), "T3");
    await waitFor(() =>
      expect(dir.listOrganizations).toHaveBeenLastCalledWith(expect.objectContaining({ verification_level: "T3" }))
    );
  });

  it("suspends an organization after confirmation", async () => {
    const org = {
      id: "o2", name: "Şüpheli A.Ş.", legal_id: "1", domain: "s.com", verification_level: "T2",
      verified_at: "2026-09-21T00:00:00Z", status: "ACTIVE", created_at: "2026-09-20T00:00:00Z",
    };
    vi.mocked(dir.listOrganizations).mockResolvedValue({ items: [org], limit: 50, offset: 0, has_more: false });
    vi.mocked(dir.setSuspended).mockResolvedValue({ ...org, status: "SUSPENDED" });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `${m.suspend}: Şüpheli A.Ş.` }));
    await userEvent.click(screen.getByRole("button", { name: m.confirm }));
    await waitFor(() => expect(dir.setSuspended).toHaveBeenCalledWith("organizations", "o2", true));
    expect(await screen.findByText(m.suspended)).toBeInTheDocument();
  });
});
