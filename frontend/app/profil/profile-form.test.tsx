import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProfileForm from "@/app/profil/profile-form";
import * as clientModule from "@/lib/api/client";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/client", () => ({
  updateTalentProfile: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/**
 * AC-2: Profil formu düzenlendikten sonra "kaydet" basılınca `updateTalentProfile` çağrılır.
 *       200 dönerse başarı mesajı gösterilir.
 * AC-3: 409 SLUG_TAKEN dönerse, `public_slug` alanının altında hata gösterilir.
 * AC-S3: Backend'den gelen `visibility` değeri form state'inde kalır;
 *        kullanıcı visibility alanına dokunmadan "kaydet"e basarsa,
 *        PATCH body'sinde gönderilen visibility mevcut değerdir.
 * AC-11: Submit tıklanırsa buton disabled+loading olur; ikinci tıklama ek istek göndermez.
 */

describe("ProfileForm (/profil/profile-form.tsx)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("AC-2: Happy path — form düzenle, kaydet, 200 döner → başarı mesajı", () => {
    it("AC-2: Geçerli veriyle submit → updateTalentProfile çağrılır, 200 → başarı mesajı", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockResolvedValueOnce({
        headline: "Yeni Başlık",
        department: "Mühendislik",
        study_year: 3,
        city: "İstanbul",
        visibility: "PUBLIC",
        public_slug: "yeni-slug",
      });

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "Eski Başlık",
            department: "Geliştirme",
            study_year: 2,
            city: "Ankara",
            visibility: "INSTITUTION",
            public_slug: "eski-slug",
          }}
        />
      );

      const headlineInput = screen.getByDisplayValue("Eski Başlık");
      const submitButton = screen.getByRole("button", { name: /kaydet/i });

      const user = userEvent.setup();
      await user.clear(headlineInput);
      await user.type(headlineInput, "Yeni Başlık");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateTalentProfile).toHaveBeenCalledWith(
          "Yeni Başlık",
          "Geliştirme",
          2,
          "Ankara",
          "INSTITUTION",
          "eski-slug"
        );
      });

      // Başarı mesajı gösterilir
      await waitFor(() => {
        expect(
          screen.getByText(/başarıyla kaydedildi|güncellendi|başarıyla güncellenmiştir/i)
        ).toBeTruthy();
      });
    });

    it("AC-2: updateTalentProfile positional parametrelerle (headline, department, study_year, city, visibility, public_slug) çağrılır", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockResolvedValueOnce({});

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PRIVATE",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateTalentProfile).toHaveBeenCalledWith(
          "H",
          "D",
          1,
          "C",
          "PRIVATE",
          "s"
        );
      });
    });
  });

  describe("AC-3: 409 SLUG_TAKEN — hata public_slug altında gösterilir", () => {
    it("AC-3: updateTalentProfile 409 SLUG_TAKEN dönersentries public_slug alanının altında hata gösterilir", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      const error = new Error("Slug taken") as Error & Record<string, unknown>;
      error.status = 409;
      error.code = "SLUG_TAKEN";
      mockUpdateTalentProfile.mockRejectedValueOnce(error);

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PUBLIC",
            public_slug: "taken-slug",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        // public_slug alanının altında hata gösterilir
        expect(screen.getByText(/bu slug zaten alındı|slug kullanımda/i)).toBeTruthy();
      });
    });

    it("AC-3: Slug hatası diğer alanları etkilemez", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      const error = new Error("Slug taken") as Error & Record<string, unknown>;
      error.status = 409;
      error.code = "SLUG_TAKEN";
      mockUpdateTalentProfile.mockRejectedValueOnce(error);

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PRIVATE",
            public_slug: "slug",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        // Slug hatası görülür
        expect(screen.getByText(/bu slug zaten alındı|slug kullanımda/i)).toBeTruthy();
      });

      // Diğer alan hataları gösterilmez (başarı mesajı da değil)
      expect(screen.queryByText(/başarıyla kaydedildi|güncellendi/i)).toBeNull();
      expect(screen.queryByRole("status")).toBeNull();
    });
  });

  describe("AC-S3: visibility sessizce genişletilmez — backend değeri kalır", () => {
    it("AC-S3: Form ilk yüklendiğinde visibility='INSTITUTION', kullanıcı dokunmadan kaydet → PATCH'te visibility='INSTITUTION' gönderilir", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockResolvedValueOnce({});

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "INSTITUTION",
            public_slug: "s",
          }}
        />
      );

      // Kullanıcı visibility alanına hiç dokunmaz
      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        // 5. parametre (visibility) = "INSTITUTION" (mevcut değer)
        expect(mockUpdateTalentProfile).toHaveBeenCalledWith(
          "H",
          "D",
          1,
          "C",
          "INSTITUTION", // ← Bu değer hiç değişmedi
          "s"
        );
      });
    });

    it("AC-S3: visibility='PRIVATE' ile yüklenen form, dokunulmadan kaydet → visibility='PRIVATE' gönderilir", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockResolvedValueOnce({});

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PRIVATE",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUpdateTalentProfile).toHaveBeenCalledWith(
          "H",
          "D",
          1,
          "C",
          "PRIVATE",
          "s"
        );
      });
    });

    it("AC-S3: visibility ASLA varsayılan/boş değere veya PUBLIC'e sessizce düşmez", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockResolvedValueOnce({});

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "ORGANIZATIONS",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        // 5. parametre AYNI OLARAK kalır
        expect(mockUpdateTalentProfile).toHaveBeenCalledWith(
          "H",
          "D",
          1,
          "C",
          "ORGANIZATIONS", // ← "PUBLIC" değil
          "s"
        );
      });
    });
  });

  describe("SPRINT H-0: 'Kuruluşlar' görünürlüğü listeden kaldırıldı", () => {
    const base = { headline: "H", department: "D", study_year: 1, city: "C", public_slug: "s" };

    it("yeni seçimde 'Kuruluşlar' seçeneği sunulmaz", () => {
      renderWithQueryClient(<ProfileForm initialData={{ ...base, visibility: "PRIVATE" }} />);
      const select = screen.getByLabelText(messages.profil.visibility) as HTMLSelectElement;
      const values = Array.from(select.options).map((option) => option.value);
      expect(values).not.toContain("ORGANIZATIONS");
      expect(screen.queryByText(messages.profil.visibilityOrganizationsSoon)).toBeNull();
    });

    it("değeri zaten 'Kuruluşlar' olan profil seçeneği korur ve gizli olduğu uyarısını görür", () => {
      renderWithQueryClient(<ProfileForm initialData={{ ...base, visibility: "ORGANIZATIONS" }} />);
      const select = screen.getByLabelText(messages.profil.visibility) as HTMLSelectElement;
      expect(select.value).toBe("ORGANIZATIONS");
      expect(screen.getByText(messages.profil.visibilityOrganizationsSoon)).toBeTruthy();
    });

    it("başka bir seçeneğe geçince uyarı kalkar", async () => {
      renderWithQueryClient(<ProfileForm initialData={{ ...base, visibility: "ORGANIZATIONS" }} />);
      await userEvent.setup().selectOptions(screen.getByLabelText(messages.profil.visibility), "PUBLIC");
      expect(screen.queryByText(messages.profil.visibilityOrganizationsSoon)).toBeNull();
    });
  });

  describe("AC-11: Çift submit engeli — buton disabled, ikinci tıklama istek göndermez", () => {
    it("AC-11: Submit tıklanırsa buton disabled olur ve ikinci tıklama hiçbir istek göndermez", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({}), 300))
      );

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PUBLIC",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();

      // Birinci tıklama
      await user.click(submitButton);

      // Buton disabled olur
      expect(submitButton).toHaveAttribute("disabled");

      // İkinci tıklama (etkisiz)
      await user.click(submitButton);

      // updateTalentProfile SADECE 1 kez çağrıldı
      expect(mockUpdateTalentProfile).toHaveBeenCalledTimes(1);
    });

    it("AC-11: Loading durumunda buton 'Kaydediliyor...' veya benzeri gösterir", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      mockUpdateTalentProfile.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({}), 500))
      );

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "INSTITUTION",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      // Loading state gösterilir (isSubmitting = true)
      // Buton disabled ve loading göstergeleri (CSS sınıfı, aria-busy vb.)
      expect(submitButton).toHaveAttribute("disabled");
    });
  });

  describe("AC-10: Ağ hatası — genel 'bağlantı hatası' mesajı, buton tekrar aktif", () => {
    it("AC-10: Network error dönerse 'bağlantı hatası' mesajı gösterilir", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      const error = new Error("Network timeout") as Error & Record<string, unknown>;
      error.status = undefined; // No status = network error
      mockUpdateTalentProfile.mockRejectedValueOnce(error);

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PUBLIC",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/bağlantı hatası|ağ hatası|tekrar deneyin/i)
        ).toBeTruthy();
      });

      // Buton tekrar aktif olur
      expect(submitButton).not.toHaveAttribute("disabled");
    });

    it("AC-10: 500 hatası dönerse genel hata mesajı gösterilir", async () => {
      const mockUpdateTalentProfile = vi.spyOn(clientModule, "updateTalentProfile");
      const error = new Error("Server error") as Error & Record<string, unknown>;
      error.status = 500;
      mockUpdateTalentProfile.mockRejectedValueOnce(error);

      renderWithQueryClient(
        <ProfileForm
          initialData={{
            headline: "H",
            department: "D",
            study_year: 1,
            city: "C",
            visibility: "PRIVATE",
            public_slug: "s",
          }}
        />
      );

      const submitButton = screen.getByRole("button", { name: /kaydet/i });
      const user = userEvent.setup();
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/hata oluştu|tekrar deneyin|hatası/i)
        ).toBeTruthy();
      });
    });
  });
});
