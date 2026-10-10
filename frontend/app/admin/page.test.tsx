import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminHomePage from "@/app/admin/page";
import { useSession } from "@/lib/session/use-session";

vi.mock("@/lib/session/use-session");

/**
 * admin-sayfalama-ve-kabuk — AC-5: /admin kök sayfası admin ekranlarına bağlantı verir.
 */
describe("AdminHomePage (/admin)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: "admin-1", email: "admin@test.com", is_platform_admin: true },
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

  afterEach(() => {
    cleanup();
  });

  it("üç admin ekranına bağlantı verir", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AdminHomePage />
      </QueryClientProvider>
    );

    const main = screen.getByRole("main");
    const hrefs = Array.from(main.querySelectorAll("a")).map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/admin/dogrulama-kuyrugu");
    expect(hrefs).toContain("/admin/skiller");
    expect(hrefs).toContain("/admin/sahtekarlik-isaretleri");
  });
});
