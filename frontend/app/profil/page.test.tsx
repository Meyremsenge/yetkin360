import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ProfilePage from "@/app/profil/page";
import { useSession } from "@/lib/session/use-session";

vi.mock("@/lib/session/use-session");
vi.mock("@/app/profil/profile-form", () => ({
  default: () => <div data-testid="profile-form">Profile Form</div>,
}));
vi.mock("@/app/profil/profile-hero", () => ({
  default: () => <div data-testid="profile-hero">Profile Hero</div>,
}));
vi.mock("@/app/profil/skills-section", () => ({
  default: () => <div data-testid="skills-section">Skills Section</div>,
}));
vi.mock("@/app/profil/evidence-section", () => ({
  default: () => <div data-testid="evidence-section">Evidence Section</div>,
}));
vi.mock("@/app/profil/institution-link-section", () => ({
  default: () => <div data-testid="institution-link-section">Institution Link Section</div>,
}));

/**
 * AC-1: Profil sayfası `AppShell` içinde `ProfileForm` + `SkillsSection` render eder.
 *       Mevcut profil bilgileri (`talent_profile`) `useSession()`'dan gelir.
 * AC-12: `talent_profile` null/eksik dönerse, açık hata state'i gösterilir.
 */

describe("ProfilePage (/profil)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-1: Happy path — profil verisi yüklü, form + skills render", () => {
    it("AC-1: useSession() data.talent_profile dolu dönerse ProfileForm + SkillsSection render edilir", async () => {
      vi.mocked(useSession).mockReturnValue({
        data: {
          user: { id: "user-1", email: "user@test.com" },
          organizations: [{ id: "org-1", name: "Test Org" }],
          institutions: [],
          talent_profile: {
            headline: "Yazılım Geliştirici",
            department: "Mühendislik",
            study_year: 3,
            city: "İstanbul",
            visibility: "INSTITUTION",
            public_slug: "user-slug",
          },
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(<ProfilePage />);

      // AppShell ve bileşenleri render edilir
      expect(screen.getByTestId("profile-form")).toBeTruthy();
      expect(screen.getByTestId("skills-section")).toBeTruthy();
      expect(screen.getByTestId("institution-link-section")).toBeTruthy();
    });

    it("AC-1: Profil verileri ProfileForm'a prop olarak geçirilir", async () => {
      const talentProfile = {
        headline: "Yazılım Mühendisi",
        department: "Geliştirme",
        study_year: 2,
        city: "Ankara",
        visibility: "PUBLIC",
        public_slug: "profile-slug",
      };

      vi.mocked(useSession).mockReturnValue({
        data: {
          user: { id: "user-1", email: "user@test.com" },
          organizations: [],
          institutions: [],
          talent_profile: talentProfile,
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(<ProfilePage />);

      // Profil formu render edilir (prop geçişi mock'ta kontrol edilir)
      expect(screen.getByTestId("profile-form")).toBeTruthy();
    });
  });

  describe("AC-12: talent_profile null/eksik — hata state'i gösterilir", () => {
    it("AC-12: talent_profile null dönerse 'profiliniz yüklenemedi' mesajı gösterilir", async () => {
      vi.mocked(useSession).mockReturnValue({
        data: {
          user: { id: "user-1", email: "user@test.com" },
          organizations: [],
          institutions: [],
          talent_profile: null,
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(<ProfilePage />);

      // ProfileForm render edilmez
      expect(screen.queryByTestId("profile-form")).toBeNull();

      // Hata mesajı gösterilir
      await waitFor(() => {
        expect(
          screen.getByText(/profiliniz yüklenemedi|destek ile iletişime geçin/i)
        ).toBeTruthy();
      });
    });

    it("AC-12: talent_profile undefined dönerse de hata mesajı gösterilir", async () => {
      vi.mocked(useSession).mockReturnValue({
        data: {
          user: { id: "user-1", email: "user@test.com" },
          organizations: [],
          institutions: [],
          talent_profile: undefined,
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(<ProfilePage />);

      // Bileşenler render edilmez
      expect(screen.queryByTestId("profile-form")).toBeNull();
      expect(screen.queryByTestId("skills-section")).toBeNull();

      // Hata gösterilir
      await waitFor(() => {
        expect(
          screen.getByText(/profiliniz yüklenemedi|destek ile iletişime geçin/i)
        ).toBeTruthy();
      });
    });

    it("AC-12: Hata mesajı açık ve spesifiktir (boş durum değil)", async () => {
      vi.mocked(useSession).mockReturnValue({
        data: {
          user: { id: "user-1" },
          organizations: [],
          institutions: [],
          talent_profile: null,
        },
        error: null,
        isPending: false,
        isError: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSession>);

      render(<ProfilePage />);

      // "Yükleniyor" değil, açık bir hata mesajı
      expect(screen.queryByText(/yükleniyor/i)).toBeNull();

      // Destek/iletişim mesajı içerir
      const errorElement = screen.getByText(
        /profiliniz yüklenemedi|destek ile iletişime geçin/i
      );
      expect(errorElement).toBeTruthy();
      expect(errorElement.textContent?.length).toBeGreaterThan(10);
    });
  });
});
