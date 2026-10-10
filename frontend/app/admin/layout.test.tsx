import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import AdminLayout from "@/app/admin/layout";
import { useSession } from "@/lib/session/use-session";

vi.mock("@/lib/session/use-session");

const replace = vi.fn();
let pathname = "/admin";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => pathname,
}));

function mockSession(partial: Record<string, unknown>) {
  vi.mocked(useSession).mockReturnValue({
    data: undefined,
    error: null,
    isPending: false,
    isError: false,
    ...partial,
  } as unknown as ReturnType<typeof useSession>);
}

/**
 * admin-sayfalama-ve-kabuk — AC-5, AC-S4, AC-S5: /admin UX guard.
 * Güvenlik sınırı sunucudadır; layout yalnız /me'deki is_platform_admin'e bakar.
 */
describe("AdminLayout guard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    pathname = "/admin";
  });

  afterEach(() => {
    cleanup();
  });

  it("admin ise çocukları render eder, yönlendirmez", () => {
    mockSession({ data: { user: { id: "a", is_platform_admin: true } } });

    render(
      <AdminLayout>
        <p>gizli-icerik</p>
      </AdminLayout>
    );

    expect(screen.getByText("gizli-icerik")).toBeTruthy();
    expect(replace).not.toHaveBeenCalled();
  });

  it("admin değilse çocukları render etmez ve /admin/giris'e yönlendirir", () => {
    mockSession({ data: { user: { id: "u", is_platform_admin: false } } });

    render(
      <AdminLayout>
        <p>gizli-icerik</p>
      </AdminLayout>
    );

    expect(screen.queryByText("gizli-icerik")).toBeNull();
    expect(replace).toHaveBeenCalledWith("/admin/giris");
  });

  it("is_platform_admin alanı yoksa fail-closed: render yok, yönlendirme var", () => {
    mockSession({ data: { user: { id: "u" } } });

    render(
      <AdminLayout>
        <p>gizli-icerik</p>
      </AdminLayout>
    );

    expect(screen.queryByText("gizli-icerik")).toBeNull();
    expect(replace).toHaveBeenCalledWith("/admin/giris");
  });

  it("oturum yüklenirken çocukları göstermez ve henüz yönlendirmez", () => {
    mockSession({ isPending: true });

    render(
      <AdminLayout>
        <p>gizli-icerik</p>
      </AdminLayout>
    );

    expect(screen.queryByText("gizli-icerik")).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it("/admin/giris guard'a takılmaz (sonsuz yönlendirme yok)", () => {
    pathname = "/admin/giris";
    mockSession({ data: undefined, isError: true });

    render(
      <AdminLayout>
        <p>giris-formu</p>
      </AdminLayout>
    );

    expect(screen.getByText("giris-formu")).toBeTruthy();
    expect(replace).not.toHaveBeenCalled();
  });
});
