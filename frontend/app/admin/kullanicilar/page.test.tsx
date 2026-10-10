import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KullanicilarPage from "@/app/admin/kullanicilar/page";
import { useSession } from "@/lib/session/use-session";
import { ApiError, NetworkError } from "@/lib/api/errors";
import * as dir from "@/lib/api/admin-directory";
import messages from "@/messages/tr.json";

vi.mock("@/lib/session/use-session");
vi.mock("@/lib/api/admin-directory", async (orig) => {
  const actual = await orig<typeof import("@/lib/api/admin-directory")>();
  return { ...actual, listUsers: vi.fn(), setSuspended: vi.fn() };
});

const m = messages.adminUsers;

const user = (over: Partial<dir.AdminUser> = {}): dir.AdminUser => ({
  id: "u1",
  email: "ali@example.com",
  status: "ACTIVE",
  is_platform_admin: false,
  email_verified: true,
  created_at: "2026-09-20T00:00:00Z",
  ...over,
});

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <KullanicilarPage />
    </QueryClientProvider>
  );
}

describe("KullanicilarPage (/admin/kullanicilar)", () => {
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

  it("renders users and requests the first page", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({ items: [user()], limit: 50, offset: 0, has_more: false });
    renderPage();
    expect(await screen.findByText("ali@example.com")).toBeInTheDocument();
    expect(dir.listUsers).toHaveBeenCalledWith(expect.objectContaining({ limit: 50, offset: 0 }));
    expect(screen.getByRole("button", { name: m.next })).toBeDisabled();
    expect(screen.getByRole("button", { name: m.prev })).toBeDisabled();
  });

  it("shows the empty state with guidance", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({ items: [], limit: 50, offset: 0, has_more: false });
    renderPage();
    expect(await screen.findByText(m.empty)).toBeInTheDocument();
  });

  it("shows an alert with retry on load failure", async () => {
    vi.mocked(dir.listUsers).mockRejectedValueOnce(new NetworkError("timeout"));
    renderPage();
    expect(await screen.findByText(messages.errors.timeout)).toBeInTheDocument();
    vi.mocked(dir.listUsers).mockResolvedValue({ items: [user()], limit: 50, offset: 0, has_more: false });
    await userEvent.click(screen.getByRole("button", { name: messages.errors.retry }));
    expect(await screen.findByText("ali@example.com")).toBeInTheDocument();
  });

  it("paginates with Sonraki when has_more is true", async () => {
    vi.mocked(dir.listUsers)
      .mockResolvedValueOnce({ items: [user()], limit: 50, offset: 0, has_more: true })
      .mockResolvedValueOnce({ items: [user({ id: "u2", email: "veli@example.com" })], limit: 50, offset: 50, has_more: false });
    renderPage();
    await screen.findByText("ali@example.com");
    await userEvent.click(screen.getByRole("button", { name: m.next }));
    expect(await screen.findByText("veli@example.com")).toBeInTheDocument();
    expect(dir.listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50 }));
  });

  it("searches with the typed term from the first page", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({ items: [], limit: 50, offset: 0, has_more: false });
    renderPage();
    await screen.findByText(m.empty);
    await userEvent.type(screen.getByLabelText(m.searchLabel), "ali");
    await userEvent.click(screen.getByRole("button", { name: m.searchButton }));
    await waitFor(() =>
      expect(dir.listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ q: "ali", offset: 0 }))
    );
    expect(await screen.findByText(m.emptyFiltered)).toBeInTheDocument();
  });

  it("suspends only after confirmation", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({ items: [user()], limit: 50, offset: 0, has_more: false });
    vi.mocked(dir.setSuspended).mockResolvedValue(user({ status: "SUSPENDED" }));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `${m.suspend}: ali@example.com` }));
    expect(dir.setSuspended).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: m.confirm }));
    await waitFor(() => expect(dir.setSuspended).toHaveBeenCalledWith("users", "u1", true));
    expect(await screen.findByText(m.suspended)).toBeInTheDocument();
  });

  it("cancel closes the dialog without a request", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({ items: [user()], limit: 50, offset: 0, has_more: false });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `${m.suspend}: ali@example.com` }));
    await userEvent.click(screen.getByRole("button", { name: m.cancel }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(dir.setSuspended).not.toHaveBeenCalled();
  });

  it("shows the last-admin message on 409", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({
      items: [user({ is_platform_admin: true })], limit: 50, offset: 0, has_more: false,
    });
    vi.mocked(dir.setSuspended).mockRejectedValue(
      new ApiError({ status: 409, code: "LAST_ADMIN_PROTECTED", message: "x", requestId: null })
    );
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: `${m.suspend}: ali@example.com` }));
    await userEvent.click(screen.getByRole("button", { name: m.confirm }));
    expect(await screen.findByText(m.lastAdmin)).toBeInTheDocument();
  });

  it("offers reactivate for suspended and nothing for deleted users", async () => {
    vi.mocked(dir.listUsers).mockResolvedValue({
      items: [user({ status: "SUSPENDED" }), user({ id: "u3", email: "gone@example.com", status: "DELETED" })],
      limit: 50, offset: 0, has_more: false,
    });
    renderPage();
    expect(await screen.findByRole("button", { name: `${m.reactivate}: ali@example.com` })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /gone@example.com/ })).not.toBeInTheDocument();
  });
});
