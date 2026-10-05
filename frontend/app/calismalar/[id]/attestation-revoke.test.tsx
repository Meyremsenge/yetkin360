import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AttestationRevoke } from "./attestation-revoke";
import { revokeAttestation } from "@/lib/api/attestations";
import { ApiError } from "@/lib/api/errors";
import type { EngagementAttestation } from "@/lib/api/engagements";

vi.mock("@/lib/api/attestations", () => ({
  revokeAttestation: vi.fn(),
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

const activeAttestation: EngagementAttestation = {
  id: "att-1",
  claim_type: "COMPETENCE",
  requested_claim_type: "COMPETENCE",
  attestor_user_id: "user-9",
  created_at: "2026-09-27T10:00:00Z",
  revoked_at: null,
  revoke_reason: null,
};

describe("AttestationRevoke", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("aktif tanıklıkta gerekçe alanı + Geri Çek butonu render edilir", () => {
    renderWithQueryClient(<AttestationRevoke attestation={activeAttestation} onSuccess={vi.fn()} />);

    expect(screen.getByLabelText("Geri çekme gerekçesi")).toBeTruthy();
    expect(screen.getByText("Geri Çek")).toBeTruthy();
  });

  it("geri çekilmiş tanıklıkta buton yerine rozet + gerekçe gösterilir", () => {
    const revoked: EngagementAttestation = {
      ...activeAttestation,
      revoked_at: "2026-10-01T00:00:00Z",
      revoke_reason: "Yanlış girilmiş",
    };
    renderWithQueryClient(<AttestationRevoke attestation={revoked} onSuccess={vi.fn()} />);

    expect(screen.getByText("Geri çekildi: Yanlış girilmiş")).toBeTruthy();
    expect(screen.queryByText("Geri Çek")).toBeNull();
  });

  it("happy path: gerekçe girilip gönderilince revokeAttestation çağrılır, başarı mesajı gösterilir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(revokeAttestation).mockResolvedValueOnce({
      id: "att-1",
      revoked_at: "2026-10-05T10:00:00Z",
      revoke_reason: "Yanlış girilmiş",
    });

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationRevoke attestation={activeAttestation} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Geri çekme gerekçesi"), "Yanlış girilmiş");
    await user.click(screen.getByText("Geri Çek"));

    await waitFor(() => {
      expect(revokeAttestation).toHaveBeenCalledWith("att-1", "Yanlış girilmiş");
      expect(screen.getByText("Tanıklık geri çekildi.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("403 FORBIDDEN → sadece attestor geri çekebilir mesajı gösterilir", async () => {
    vi.mocked(revokeAttestation).mockRejectedValueOnce(
      new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationRevoke attestation={activeAttestation} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Geri çekme gerekçesi"), "x");
    await user.click(screen.getByText("Geri Çek"));

    await waitFor(() => {
      expect(screen.getByText("Sadece kendi verdiğiniz tanıklığı geri çekebilirsiniz.")).toBeTruthy();
    });
  });

  it("409 ALREADY_REVOKED → zaten geri çekilmiş mesajı gösterilir ve onSuccess (refetch) tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(revokeAttestation).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "ALREADY_REVOKED", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationRevoke attestation={activeAttestation} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Geri çekme gerekçesi"), "x");
    await user.click(screen.getByText("Geri Çek"));

    await waitFor(() => {
      expect(screen.getByText("Bu tanıklık zaten geri çekilmiş.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("422 VALIDATION_ERROR → gerekçe zorunlu mesajı gösterilir", async () => {
    vi.mocked(revokeAttestation).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "VALIDATION_ERROR", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<AttestationRevoke attestation={activeAttestation} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Geri çekme gerekçesi"), "x");
    await user.click(screen.getByText("Geri Çek"));

    await waitFor(() => {
      expect(screen.getByText("Geri çekme gerekçesi zorunludur.")).toBeTruthy();
    });
  });
});
