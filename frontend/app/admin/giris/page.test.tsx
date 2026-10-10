import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdminLoginPage from "@/app/admin/giris/page";
import LoginPage from "@/app/giris/page";
import messages from "@/messages/tr.json";
import * as clientModule from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  login: vi.fn(),
  apiFetch: vi.fn(),
}));

vi.mock("@/lib/session/use-session", () => ({
  useSession: vi.fn(),
  SESSION_QUERY_KEY: ["session"],
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockLogin = vi.mocked(clientModule.login);
const mockApiFetch = vi.mocked(clientModule.apiFetch);

function loginResult(role: string) {
  return { user_id: "u-1", role, email_verified: true };
}

async function submit(email = "admin@example.com", password = "S3cret-pass!") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(messages.giris.emailLabel), email);
  await user.type(screen.getByLabelText(messages.giris.passwordLabel), password);
  await user.click(screen.getByRole("button", { name: messages.giris.login }));
}

describe("AdminLoginPage (/admin/giris)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiFetch.mockResolvedValue(undefined);
  });

  it("yönetici başlığını ve öğrenci/kuruluş girişine dönüş linkini gösterir", async () => {
    render(await AdminLoginPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(messages.adminGiris.title);
    expect(screen.getByText(messages.adminGiris.subtitle)).toBeTruthy();
    expect(
      screen.getByRole("link", { name: messages.adminGiris.userLoginLink }).getAttribute("href")
    ).toBe("/giris");
  });

  it("admin girişinde doğrulama kuyruğuna yönlendirir", async () => {
    mockLogin.mockResolvedValue(loginResult("PLATFORM_ADMIN"));
    render(await AdminLoginPage({ searchParams: Promise.resolve({}) }));
    await submit();
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/admin/dogrulama-kuyrugu"));
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it("admin girişinde güvenli next hedefine gider", async () => {
    mockLogin.mockResolvedValue(loginResult("PLATFORM_ADMIN"));
    render(await AdminLoginPage({ searchParams: Promise.resolve({ next: "/admin/skiller" }) }));
    await submit();
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/admin/skiller"));
  });

  it.each(["TALENT", "ORG_ADMIN", "COORDINATOR", "USER"])(
    "admin olmayan hesabı (%s) içeri almaz: oturumu kapatır, genel hata gösterir",
    async (role) => {
      mockLogin.mockResolvedValue(loginResult(role));
      render(await AdminLoginPage({ searchParams: Promise.resolve({ next: "/admin/skiller" }) }));
      await submit("ogrenci@example.com");

      expect(await screen.findByText(messages.giris.invalidCredentials)).toBeTruthy();
      expect(mockApiFetch).toHaveBeenCalledWith("/auth/logout", { method: "POST" });
      expect(mockPush).not.toHaveBeenCalled();
    }
  );

  it("çıkış isteği başarısız olsa da hata gösterilir ve yönlendirme yapılmaz", async () => {
    mockLogin.mockResolvedValue(loginResult("TALENT"));
    mockApiFetch.mockRejectedValue(new Error("network"));
    render(await AdminLoginPage({ searchParams: Promise.resolve({}) }));
    await submit("ogrenci@example.com");

    expect(await screen.findByText(messages.giris.invalidCredentials)).toBeTruthy();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("hatalı şifrede normal girişle aynı mesajı gösterir", async () => {
    mockLogin.mockRejectedValue({ status: 401, code: "INVALID_CREDENTIALS" });
    render(await AdminLoginPage({ searchParams: Promise.resolve({}) }));
    await submit();
    expect(await screen.findByText(messages.giris.invalidCredentials)).toBeTruthy();
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it("oturum bittiyse uyarıyı gösterir", async () => {
    render(await AdminLoginPage({ searchParams: Promise.resolve({ neden: "oturum-bitti" }) }));
    expect(screen.getByText(messages.session.expired)).toBeTruthy();
  });
});

describe("LoginPage (/giris) — role göre varsayılan hedef", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("admin normal girişten girerse doğrulama kuyruğuna gider", async () => {
    mockLogin.mockResolvedValue(loginResult("PLATFORM_ADMIN"));
    render(await LoginPage({ searchParams: Promise.resolve({}) }));
    await submit();
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/admin/dogrulama-kuyrugu"));
  });

  it("öğrenci normal girişten girerse Çalışmalarım'a gider ve oturumu kapatılmaz", async () => {
    mockLogin.mockResolvedValue(loginResult("TALENT"));
    render(await LoginPage({ searchParams: Promise.resolve({}) }));
    await submit("ogrenci@example.com");
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/calismalar"));
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it("yönetici girişi linkini gösterir", async () => {
    render(await LoginPage({ searchParams: Promise.resolve({}) }));
    expect(
      screen.getByRole("link", { name: messages.adminGiris.linkFromLogin }).getAttribute("href")
    ).toBe("/admin/giris");
  });
});
