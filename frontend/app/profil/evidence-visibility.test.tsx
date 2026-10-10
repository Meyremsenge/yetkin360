import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import EvidenceSection from "@/app/profil/evidence-section";
import {
  getMySignals,
  getMyVerifiedExperiences,
  setMyVerifiedExperienceVisibility,
} from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  getMySignals: vi.fn(),
  getMyVerifiedExperiences: vi.fn(),
  setMyVerifiedExperienceVisibility: vi.fn(),
}));

function renderSection() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <EvidenceSection />
    </QueryClientProvider>
  );
}

function experience(visibility: string) {
  return {
    id: "ve-1",
    organization_name_snapshot: "Lale Yazılım A.Ş.",
    role_snapshot: "Backend Geliştirme Stajı",
    started_on_snapshot: "2026-07-01",
    ended_on_snapshot: "2026-09-29",
    institution_name_snapshot: null,
    claim_type: "COMPETENCE",
    visibility,
    public_token: "tok-1",
    created_at: "2026-10-01T10:00:00Z",
  };
}

describe("EvidenceSection — doğrulanmış deneyim görünürlüğü", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getMySignals).mockResolvedValue({ items: [] });
  });
  afterEach(() => cleanup());

  it("gizli deneyimde anahtar kapalıdır ve doğrulama linki yoktur", async () => {
    vi.mocked(getMyVerifiedExperiences).mockResolvedValue({ items: [experience("PRIVATE")] });
    renderSection();

    const toggle = await screen.findByRole("switch", { name: "Herkese açık" });
    expect(toggle.getAttribute("aria-checked")).toBe("false");
    expect(screen.queryByRole("link", { name: /Doğrulama kaydı/ })).toBeNull();
  });

  it("anahtara basınca PUBLIC isteği gider ve liste yenilenir", async () => {
    vi.mocked(getMyVerifiedExperiences)
      .mockResolvedValueOnce({ items: [experience("PRIVATE")] })
      .mockResolvedValue({ items: [experience("PUBLIC")] });
    vi.mocked(setMyVerifiedExperienceVisibility).mockResolvedValue({});
    renderSection();

    fireEvent.click(await screen.findByRole("switch", { name: "Herkese açık" }));

    await waitFor(() => expect(setMyVerifiedExperienceVisibility).toHaveBeenCalledWith("ve-1", "PUBLIC"));
    await waitFor(() =>
      expect(screen.getByRole("switch", { name: "Herkese açık" }).getAttribute("aria-checked")).toBe("true")
    );
    expect(screen.getByRole("link", { name: /Doğrulama kaydı/ }).getAttribute("href")).toBe("/v/tok-1");
  });

  it("açık deneyimi kapatınca PRIVATE gönderilir", async () => {
    vi.mocked(getMyVerifiedExperiences).mockResolvedValue({ items: [experience("PUBLIC")] });
    vi.mocked(setMyVerifiedExperienceVisibility).mockResolvedValue({});
    renderSection();

    fireEvent.click(await screen.findByRole("switch", { name: "Herkese açık" }));

    await waitFor(() => expect(setMyVerifiedExperienceVisibility).toHaveBeenCalledWith("ve-1", "PRIVATE"));
  });

  it("istek başarısızsa hata duyurulur, anahtar durumu değişmez", async () => {
    vi.mocked(getMyVerifiedExperiences).mockResolvedValue({ items: [experience("PRIVATE")] });
    vi.mocked(setMyVerifiedExperienceVisibility).mockRejectedValue(new Error("boom"));
    renderSection();

    const toggle = await screen.findByRole("switch", { name: "Herkese açık" });
    fireEvent.click(toggle);

    expect(await screen.findByText("Görünürlük değiştirilemedi. Tekrar deneyin.")).toBeTruthy();
    expect(toggle.getAttribute("aria-checked")).toBe("false");
  });
});
