import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EmailVerificationBanner } from "@/components/email-verification-banner";
import { resendVerification } from "@/lib/api/client";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/client", () => ({
  resendVerification: vi.fn(),
}));

const text = messages.emailVerificationBanner;

describe("EmailVerificationBanner (YET-196)", () => {
  beforeEach(() => {
    vi.mocked(resendVerification).mockReset();
  });

  it("açıklama ve yeniden gönder düğmesini gösterir", () => {
    render(<EmailVerificationBanner />);
    expect(screen.getByText(text.message)).toBeTruthy();
    expect(screen.getByRole("button", { name: text.resend })).toBeTruthy();
  });

  it("düğmeye basınca resendVerification bir kez çağrılır ve 'sent' mesajı görünür", async () => {
    vi.mocked(resendVerification).mockResolvedValueOnce(undefined);
    render(<EmailVerificationBanner />);

    fireEvent.click(screen.getByRole("button", { name: text.resend }));

    await waitFor(() => expect(screen.getByText(text.sent)).toBeTruthy());
    expect(resendVerification).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(text.failed)).toBeNull();
  });

  it("istek sürerken düğme devre dışıdır", async () => {
    let resolve: () => void = () => {};
    vi.mocked(resendVerification).mockReturnValueOnce(new Promise<void>((r) => { resolve = r; }));
    render(<EmailVerificationBanner />);

    fireEvent.click(screen.getByRole("button", { name: text.resend }));

    const pending = await screen.findByRole("button", { name: text.sending });
    expect((pending as HTMLButtonElement).disabled).toBe(true);
    resolve();
    await waitFor(() => expect(screen.getByText(text.sent)).toBeTruthy());
  });

  it("hata olursa 'failed' mesajı gösterilir, 'sent' gösterilmez", async () => {
    vi.mocked(resendVerification).mockRejectedValueOnce(new Error("boom"));
    render(<EmailVerificationBanner />);

    fireEvent.click(screen.getByRole("button", { name: text.resend }));

    await waitFor(() => expect(screen.getByText(text.failed)).toBeTruthy());
    expect(screen.queryByText(text.sent)).toBeNull();
  });
});
