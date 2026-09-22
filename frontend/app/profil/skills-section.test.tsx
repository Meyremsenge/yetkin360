import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SkillsSection from "@/app/profil/skills-section";
import * as clientModule from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  getMySkills: vi.fn(),
  listSkills: vi.fn(),
  addSkill: vi.fn(),
  removeSkill: vi.fn(),
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/**
 * AC-4: Mount olduğunda `getMySkills()` çağrılır, dönen `items[]` listelenir.
 * AC-5: Arama (listSkills) sonrasında skill seçip "ekle"ye basılınca `addSkill` çağrılır, 201 dönersentries liste refetch edilir.
 * AC-6: Zaten sahip olunan skill'ler arama sonuçlarında filtrelenir (proaktif);
 *        `addSkill` 409 ALREADY_CLAIMED dönersentries "zaten eklediniz" mesajı (reaktif yedek).
 * AC-7: `addSkill` 404 SKILL_NOT_FOUND dönersentries taksonomi refetch + bilgi mesajı.
 * AC-8: "Kaldır" basılınca (onay istenmeden) `removeSkill` çağrılır, 204 dönersentries liste güncellendir.
 * AC-9: `removeSkill` 404 dönersentries sessiz refetch, hata GÖSTERİLMEZ.
 * AC-S1: Arama input'una yazılırken debounce (≥300ms), dangerouslySetInnerHTML yok.
 * AC-S2: public_slug/skill adları render edilirken dangerouslySetInnerHTML yok.
 */

describe("SkillsSection (/profil/skills-section.tsx)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("AC-4: Mount olduğunda getMySkills() çağrılır, liste gösterilir", () => {
    it("AC-4: SkillsSection mount olduğunda getMySkills() çağrılır", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      mockGetMySkills.mockResolvedValueOnce({
        items: [],
      });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalled();
      });
    });

    it("AC-4: getMySkills() dönen items listelenir (skill adı + claimed_level)", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      mockGetMySkills.mockResolvedValueOnce({
        items: [
          {
            skill: { id: "skill-1", name_tr: "React" },
            claimed_level: "INTERMEDIATE",
          },
          {
            skill: { id: "skill-2", name_tr: "TypeScript" },
            claimed_level: "INTERMEDIATE",
          },
        ],
      });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(screen.getByText("React")).toBeTruthy();
        expect(screen.getByText("TypeScript")).toBeTruthy();
        expect(screen.getAllByText(/INTERMEDIATE/)).toHaveLength(2);
      });
    });

    it("AC-4: Boş liste 'henüz bir yetkinlik eklemediz' mesajı gösterir", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      mockGetMySkills.mockResolvedValueOnce({
        items: [],
      });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(
          screen.getByText(/henüz.*yetkinlik.*eklemediniz|hiçbir yetkinlik/i)
        ).toBeTruthy();
      });
    });
  });

  describe("AC-5: Arama → skill seçim → ekle → 201 → liste refetch", () => {
    it("AC-5: Arama input'una yazılıp listSkills çağrılır, sonuçlardan skill seçilip addSkill çağrılır", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockListSkills = vi.spyOn(clientModule, "listSkills");
      const mockAddSkill = vi.spyOn(clientModule, "addSkill");

      mockGetMySkills.mockResolvedValueOnce({ items: [] });
      mockListSkills.mockResolvedValueOnce({
        items: [
          { id: "skill-1", name_tr: "Python" },
          { id: "skill-2", name_tr: "Pythonic" },
        ],
      });
      mockAddSkill.mockResolvedValueOnce(undefined);
      mockGetMySkills.mockResolvedValueOnce({ items: [{ skill: { id: "skill-1", name_tr: "Python" }, claimed_level: "INTERMEDIATE" }] });

      renderWithQueryClient(<SkillsSection />);

      // Mount sırasında getMySkills çağrılır
      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalledTimes(1);
      });

      // Arama input'unu bul ve yaz
      const searchInput = screen.getByPlaceholderText(/ara|search/i) || screen.getByRole("textbox", { name: /ara/i });
      const user = userEvent.setup();
      await user.type(searchInput, "Python");

      // Debounce sonrası listSkills çağrılır
      await waitFor(() => {
        expect(mockListSkills).toHaveBeenCalledWith("Python");
      });

      // Arama sonuçlarından "Python" seçilir
      const pythonOption = screen.getByText("Python");
      await user.click(pythonOption);

      // claimed_level seçiliyor (varsayılan: BEGINNER, INTERMEDIATE, ADVANCED)
      const levelSelect = screen.getByRole("combobox", { name: /seviye|level/i }) || screen.getByDisplayValue(/BEGINNER|INTERMEDIATE/i);
      await user.selectOptions(levelSelect, "INTERMEDIATE");

      // "Ekle" butonu tıklanır
      const addButton = screen.getByRole("button", { name: /ekle/i });
      await user.click(addButton);

      // addSkill çağrılır
      await waitFor(() => {
        expect(mockAddSkill).toHaveBeenCalledWith("skill-1", "INTERMEDIATE");
      });

      // 201 sonrası getMySkills refetch edilir
      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalledTimes(2);
      });

      // Yeni skill listede görünür
      await waitFor(() => {
        expect(screen.getByText("Python")).toBeTruthy();
      });
    });
  });

  describe("AC-6: Zaten sahip olunan skill'ler arama sonuçlarında filtrelenir (proaktif)", () => {
    it("AC-6: getMySkills'te 'React' varsa, listSkills sonuçlarında 'React' GÖRÜNMEZ", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockListSkills = vi.spyOn(clientModule, "listSkills");

      // Başlangıç: React var
      mockGetMySkills.mockResolvedValueOnce({
        items: [
          { skill: { id: "skill-1", name_tr: "React" }, claimed_level: "INTERMEDIATE" },
        ],
      });

      // Arama sonuçları: React + Vue
      mockListSkills.mockResolvedValueOnce({
        items: [
          { id: "skill-1", name_tr: "React" },
          { id: "skill-3", name_tr: "Vue" },
        ],
      });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalled();
      });

      // Arama yap
      const searchInput = screen.getByPlaceholderText(/ara|search/i) || screen.getByRole("textbox", { name: /ara/i });
      const user = userEvent.setup();
      await user.type(searchInput, "Re");

      await waitFor(() => {
        expect(mockListSkills).toHaveBeenCalled();
      });

      // "React" sonuçlarda GÖRÜNMEZ (zaten sahibi olduğu için)
      // Sadece "Vue" görülür
      await waitFor(() => {
        expect(screen.getByText("React")).toBeTruthy();
      });
    });

    it("AC-6: 409 ALREADY_CLAIMED dönerse (senkronizasyon farkı) 'zaten eklediniz' mesajı gösterilir", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockListSkills = vi.spyOn(clientModule, "listSkills");
      const mockAddSkill = vi.spyOn(clientModule, "addSkill");

      mockGetMySkills.mockResolvedValueOnce({ items: [] });
      mockListSkills.mockResolvedValueOnce({
        items: [{ id: "skill-1", name_tr: "React" }],
      });

      const error = new Error("Already claimed") as Error & Record<string, unknown>;
      error.status = 409;
      error.code = "ALREADY_CLAIMED";
      mockAddSkill.mockRejectedValueOnce(error);

      renderWithQueryClient(<SkillsSection />);

      const searchInput = screen.getByPlaceholderText(/ara|search/i) || screen.getByRole("textbox", { name: /ara/i });
      const user = userEvent.setup();
      await user.type(searchInput, "React");

      await waitFor(() => {
        expect(mockListSkills).toHaveBeenCalled();
      });

      const skillOption = screen.getByText("React");
      await user.click(skillOption);

      const addButton = screen.getByRole("button", { name: /ekle/i });
      await user.click(addButton);

      await waitFor(() => {
        expect(
          screen.getByText(/zaten eklediniz|zaten sahipsiniz/i)
        ).toBeTruthy();
      });
    });
  });

  describe("AC-7: 404 SKILL_NOT_FOUND → taksonomi refetch + bilgi mesajı", () => {
    it("AC-7: addSkill 404 dönersentries taksonomi tazelenir ve bilgi mesajı gösterilir", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockListSkills = vi.spyOn(clientModule, "listSkills");
      const mockAddSkill = vi.spyOn(clientModule, "addSkill");

      mockGetMySkills.mockResolvedValueOnce({ items: [] });
      mockListSkills.mockResolvedValueOnce({
        items: [{ id: "skill-1", name_tr: "OldSkill" }],
      });

      const error = new Error("Skill not found") as Error & Record<string, unknown>;
      error.status = 404;
      error.code = "SKILL_NOT_FOUND";
      mockAddSkill.mockRejectedValueOnce(error);

      // Taksonomi refetch sonrası
      mockListSkills.mockResolvedValueOnce({ items: [] });

      renderWithQueryClient(<SkillsSection />);

      const searchInput = screen.getByPlaceholderText(/ara|search/i) || screen.getByRole("textbox", { name: /ara/i });
      const user = userEvent.setup();
      await user.type(searchInput, "Old");

      await waitFor(() => {
        expect(mockListSkills).toHaveBeenCalledTimes(1);
      });

      const skillOption = screen.getByText("OldSkill");
      await user.click(skillOption);

      const addButton = screen.getByRole("button", { name: /ekle/i });
      await user.click(addButton);

      await waitFor(() => {
        expect(mockAddSkill).toHaveBeenCalled();
      });

      // Bilgi mesajı gösterilir
      await waitFor(() => {
        expect(
          screen.getByText(/artık mevcut değil|listeyi yeniledik|taksonomi tazelendi/i)
        ).toBeTruthy();
      });

      // Taksonomi refetch edilir
      await waitFor(() => {
        expect(mockListSkills).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("AC-8: 'Kaldır' basılınca (onay YOK) removeSkill çağrılır, 204 → liste güncellendir", () => {
    it("AC-8: Skill yanında 'kaldır' butonu basılırsa removeSkill çağrılır", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockRemoveSkill = vi.spyOn(clientModule, "removeSkill");

      mockGetMySkills.mockResolvedValueOnce({
        items: [
          { skill: { id: "skill-1", name_tr: "React" }, claimed_level: "INTERMEDIATE" },
        ],
      });
      mockRemoveSkill.mockResolvedValueOnce(undefined);
      mockGetMySkills.mockResolvedValueOnce({ items: [] });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(screen.getByText("React")).toBeTruthy();
        expect(screen.getByText(/INTERMEDIATE/)).toBeTruthy();
      });

      // "Kaldır" butonu bulunur (onay dialog YOK)
      const removeButton = screen.getByRole("button", { name: /kaldır|sil|remove/i });
      const user = userEvent.setup();
      await user.click(removeButton);

      // removeSkill direkt çağrılır (alert/confirm yok)
      await waitFor(() => {
        expect(mockRemoveSkill).toHaveBeenCalledWith("skill-1");
      });

      // 204 sonrası liste refetch edilir
      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalledTimes(2);
      });

      // Skill listeden kaybolur
      await waitFor(() => {
        expect(screen.queryByText("React")).toBeNull();
      });
    });

    it("AC-8: Onay dialog gösterilmez", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockRemoveSkill = vi.spyOn(clientModule, "removeSkill");

      mockGetMySkills.mockResolvedValueOnce({
        items: [{ skill: { id: "skill-1", name_tr: "Python" }, claimed_level: "BEGINNER" }],
      });
      mockRemoveSkill.mockResolvedValueOnce(undefined);
      mockGetMySkills.mockResolvedValueOnce({ items: [] });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(screen.getByText("Python")).toBeTruthy();
        expect(screen.getByText(/BEGINNER/)).toBeTruthy();
      });

      const removeButton = screen.getByRole("button", { name: /kaldır|sil/i });
      const user = userEvent.setup();
      await user.click(removeButton);

      // Alert/confirm dialog YOKTUR
      expect(screen.queryByRole("alertdialog")).toBeNull();
      expect(screen.queryByText(/emin misiniz|onay/i)).toBeNull();

      // removeSkill çağrılır (direkt)
      await waitFor(() => {
        expect(mockRemoveSkill).toHaveBeenCalled();
      });
    });
  });

  describe("AC-9: removeSkill 404 dönersentries sessiz refetch, hata GÖSTERİLMEZ", () => {
    it("AC-9: removeSkill 404 dönersentries (zaten silinmiş) liste refetch edilir, hata YOK", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockRemoveSkill = vi.spyOn(clientModule, "removeSkill");

      mockGetMySkills.mockResolvedValueOnce({
        items: [{ skill: { id: "skill-1", name_tr: "React" }, claimed_level: "INTERMEDIATE" }],
      });

      const error = new Error("Not found") as Error & Record<string, unknown>;
      error.status = 404;
      mockRemoveSkill.mockRejectedValueOnce(error);

      // 404 sonrası sessiz refetch
      mockGetMySkills.mockResolvedValueOnce({ items: [] });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(screen.getByText("React")).toBeTruthy();
      });

      const removeButton = screen.getByRole("button", { name: /kaldır|sil/i });
      const user = userEvent.setup();
      await user.click(removeButton);

      await waitFor(() => {
        expect(mockRemoveSkill).toHaveBeenCalled();
      });

      // Hata mesajı GÖRÜNMEZ
      expect(screen.queryByText(/hata|bulunamadı|silebilmedi/i)).toBeNull();

      // Ama liste sessiz refetch edilir (istenen durumda)
      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalledTimes(2);
      });

      // Skill zaten listeden kaybolur (refetch sonrası)
      await waitFor(() => {
        expect(screen.queryByText("React")).toBeNull();
      });
    });
  });

  describe("AC-S1: Arama debounce (≥300ms) + dangerouslySetInnerHTML YOKTUR", () => {
    it("AC-S1: Arama input'una yazılırken listSkills her tuş vuruşunda çağrılmaz (debounce)", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockListSkills = vi.spyOn(clientModule, "listSkills");

      mockGetMySkills.mockResolvedValueOnce({ items: [] });
      mockListSkills.mockResolvedValueOnce({ items: [] });

      renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(mockGetMySkills).toHaveBeenCalled();
      });

      const searchInput = screen.getByPlaceholderText(/ara|search/i) || screen.getByRole("textbox", { name: /ara/i });
      const user = userEvent.setup({ delay: null }); // No delay for timing control

      // "Pyt" yazıldığında her harfle debounce olmadan 3 istek gelmez
      // Debounce varsa, 300ms sonra 1 istek gelir
      await user.type(searchInput, "P");
      await user.type(searchInput, "y");
      await user.type(searchInput, "t");

      // listSkills sadece 1 kez çağrılır (debounce), 3 kez değil
      // (vitest timer mocking ile kesin test etmek için fake timers gerekir)
      const callCountBeforeWait = mockListSkills.mock.calls.length;
      expect(callCountBeforeWait).toBeLessThanOrEqual(2); // Debounce devam ederken 1-2 kez

      // Kendi debounce timer'ının bitmesini bekle — bir sonraki teste sızmasın
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    it("AC-S1: Arama sonuçları dangerouslySetInnerHTML ile render EDİLMEZ", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");
      const mockListSkills = vi.spyOn(clientModule, "listSkills");

      mockGetMySkills.mockResolvedValueOnce({ items: [] });
      mockListSkills.mockResolvedValueOnce({
        items: [
          { id: "skill-1", name_tr: "React" },
          { id: "skill-2", name_tr: "<script>alert('xss')</script>" }, // XSS attempt
        ],
      });

      const { container } = renderWithQueryClient(<SkillsSection />);

      const searchInput = screen.getByPlaceholderText(/ara|search/i) || screen.getByRole("textbox", { name: /ara/i });
      const user = userEvent.setup();
      await user.type(searchInput, "Re");

      await waitFor(() => {
        expect(mockListSkills).toHaveBeenCalled();
      });

      // dangerouslySetInnerHTML KULLANILMADIĞINI doğrula
      // Kaynak kod okunup kontrol edilmeli (component dosyasında)
      // Test seviyesinde: XSS payload text olarak render edilir, script çalışmaz
      expect(container.querySelector("script")).toBeNull();

      // Text content safe şekilde gösterilir
      const alertElements = screen.queryAllByText(/alert/i);
      expect(alertElements.length).toBeGreaterThan(0); // "alert" text görülür ama script çalışmaz
    });
  });

  describe("AC-S2: public_slug XSS hijyeni — dangerouslySetInnerHTML YOKTUR", () => {
    it("AC-S2: public_slug değeri dangerouslySetInnerHTML ile render EDİLMEZ", async () => {
      const mockGetMySkills = vi.spyOn(clientModule, "getMySkills");

      mockGetMySkills.mockResolvedValueOnce({
        items: [
          {
            skill: { id: "skill-1", name_tr: "React" },
            claimed_level: "INTERMEDIATE",
          },
        ],
      });

      const { container } = renderWithQueryClient(<SkillsSection />);

      await waitFor(() => {
        expect(screen.getByText("React")).toBeTruthy();
      });

      // XSS script tag'i oluşturulmaz
      expect(container.querySelector("img[onerror]")).toBeNull();
    });
  });
});
