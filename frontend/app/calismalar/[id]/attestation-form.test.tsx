import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AttestationForm } from "./attestation-form";
import { createAttestation } from "@/lib/api/attestations";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";

vi.mock("@/lib/api/attestations", () => ({
  createAttestation: vi.fn(),
}));

vi.mock("@/components/skill-picker", () => ({
  SkillPicker: ({ label }: { label: string }) => <span>{label}</span>,
}));

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return render(ui, { wrapper: Wrapper });
}

const evaluatedEngagement: EngagementDetail = {
  id: "eng-1",
  title: "Yaz Kısa Projesi",
  kind: "SHORT_PROJECT",
  status: "EVALUATED",
  organization_name: "Bulut Sistemleri Ltd.",
  talent_id: "talent-1",
  organization_id: "org-1",
  institution_id: "inst-1",
  reason: null,
  version: 4,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-18T14:30:00Z",
  tasks: [],
  deliverables: [],
  attestations: [],
};

describe("AttestationForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("EVALUATED durumunda form render edilir", () => {
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={vi.fn()} />);

    expect(screen.getByLabelText("Tanıklık Türü")).toBeTruthy();
    expect(screen.getByText("Tanıklığı Gönder")).toBeTruthy();
  });

  it("ACTIVE durumunda hiçbir şey render edilmez", () => {
    renderWithQueryClient(
      <AttestationForm engagement={{ ...evaluatedEngagement, status: "ACTIVE" }} onSuccess={vi.fn()} />
    );

    expect(screen.queryByLabelText("Tanıklık Türü")).toBeNull();
  });

  it("happy path (downgrade yok): engagement.version gönderilir, başarı mesajı gösterilir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createAttestation).mockResolvedValueOnce({
      id: "att-1", claim_type: "COMPETENCE", requested_claim_type: "COMPETENCE", downgrade_reasons: [],
    });

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={onSuccess} />);

    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(createAttestation).toHaveBeenCalledWith("eng-1", { claim_type: "COMPETENCE", version: 4, skill_id: undefined });
      expect(screen.getByText("Tanıklık gönderildi, deneyim doğrulandı.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("happy path (downgrade VAR): bilgi mesajı doğru claim_type ve reason'ları gösterir", async () => {
    vi.mocked(createAttestation).mockResolvedValueOnce({
      id: "att-2", claim_type: "PARTICIPATION", requested_claim_type: "COMPETENCE", downgrade_reasons: ["NO_DELIVERABLE"],
    });

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={vi.fn()} />);

    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      const message = screen.getByRole("status");
      expect(message.textContent).toContain("Yetkinlik");
      expect(message.textContent).toContain("Katılım");
      expect(message.textContent).toContain("Hiç çıktı gönderilmemiş");
    });
  });

  it("farklı claim_type seçilirse payload'a yansır", async () => {
    vi.mocked(createAttestation).mockResolvedValueOnce({
      id: "att-3", claim_type: "PARTICIPATION", requested_claim_type: "PARTICIPATION", downgrade_reasons: [],
    });

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText("Tanıklık Türü"), "PARTICIPATION");
    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(createAttestation).toHaveBeenCalledWith("eng-1", { claim_type: "PARTICIPATION", version: 4, skill_id: undefined });
    });
  });

  it("403 FORBIDDEN → yetki hatası mesajı", async () => {
    vi.mocked(createAttestation).mockRejectedValueOnce(
      new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={vi.fn()} />);
    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bu işlemi yapma yetkiniz yok.")).toBeTruthy();
    });
  });

  it("409 INVALID_STATE_TRANSITION → uygun mesaj + onSuccess (refetch)", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createAttestation).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "INVALID_STATE_TRANSITION", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={onSuccess} />);
    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Tanıklık yalnızca değerlendirme tamamlanmış çalışmalar için verilebilir.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("409 CONFLICT (versiyon uyuşmazlığı) → genel conflict mesajı + onSuccess (refetch)", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createAttestation).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "CONFLICT", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={onSuccess} />);
    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Kayıt başka bir işlemle değişti, güncel durum yeniden yüklendi.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("409 SELF_ATTESTATION_FORBIDDEN → uygun mesaj", async () => {
    vi.mocked(createAttestation).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "SELF_ATTESTATION_FORBIDDEN", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={vi.fn()} />);
    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Kendi deneyiminize tanıklık yapamazsınız.")).toBeTruthy();
    });
  });

  it("409 ATTESTATION_ALREADY_EXISTS → uygun mesaj + onSuccess (refetch)", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createAttestation).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "ATTESTATION_ALREADY_EXISTS", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationForm engagement={evaluatedEngagement} onSuccess={onSuccess} />);
    await user.click(screen.getByText("Tanıklığı Gönder"));

    await waitFor(() => {
      expect(screen.getByText("Bu çalışma için zaten tanıklık gönderilmiş.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
