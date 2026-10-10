import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AboutSection from "@/app/profil/about-section";
import { updateTalentAbout } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ updateTalentAbout: vi.fn() }));

function renderSection(initialAbout: string | null = null) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AboutSection initialAbout={initialAbout} />
    </QueryClientProvider>
  );
}

describe("AboutSection — Hakkımda", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("mevcut metni, sayacı ve 'Kendi beyanı' etiketini gösterir", () => {
    renderSection("Merhaba");
    expect(screen.getByLabelText("Hakkımda metni")).toHaveValue("Merhaba");
    expect(screen.getByText("7 / 1000")).toBeInTheDocument();
    expect(screen.getByText("Kendi beyanı")).toBeInTheDocument();
    expect(screen.getByText(/özel nitelikli kişisel bilgileri yazma/)).toBeInTheDocument();
  });

  it("kaydeder ve başarıyı duyurur", async () => {
    vi.mocked(updateTalentAbout).mockResolvedValue({});
    renderSection();
    fireEvent.change(screen.getByLabelText("Hakkımda metni"), { target: { value: "Veri görselleştirme seviyorum." } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));

    await waitFor(() => expect(screen.getByText("Kaydedildi")).toBeInTheDocument());
    expect(updateTalentAbout).toHaveBeenCalledWith("Veri görselleştirme seviyorum.");
  });

  it("1000 karakteri aşınca kaydetme kapanır ve sayaç uyarır", () => {
    renderSection();
    fireEvent.change(screen.getByLabelText("Hakkımda metni"), { target: { value: "a".repeat(1001) } });
    expect(screen.getByText("1001 / 1000")).toHaveClass("text-destructive");
    expect(screen.getByRole("button", { name: "Kaydet" })).toBeDisabled();
    expect(screen.getByLabelText("Hakkımda metni")).toHaveAttribute("aria-invalid", "true");
  });

  it("sunucu hatasında hata mesajı gösterir", async () => {
    vi.mocked(updateTalentAbout).mockRejectedValue(new Error("x"));
    renderSection();
    fireEvent.change(screen.getByLabelText("Hakkımda metni"), { target: { value: "Deneme" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    await waitFor(() => expect(screen.getByText("Kaydedilemedi. Tekrar dene.")).toBeInTheDocument());
  });

  it("metni düz metin olarak tutar (HTML yorumlanmaz)", () => {
    renderSection("<img src=x onerror=alert(1)>");
    expect(screen.getByLabelText("Hakkımda metni")).toHaveValue("<img src=x onerror=alert(1)>");
    expect(document.querySelector("img")).toBeNull();
  });
});
