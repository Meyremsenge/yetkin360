import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginForm from "@/app/giris/form";
import messages from "@/messages/tr.json";
import { login } from "@/lib/api/client";
import { DEMO_ACCOUNTS, DEMO_ADMIN_EMAIL, DEMO_PASSWORD, demoAccountsEnabled } from "@/lib/demo-accounts";

vi.mock("@/lib/api/client", () => ({ login: vi.fn(), apiFetch: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("Login demo accounts panel", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("is hidden unless enabled", () => {
    render(<LoginForm />);
    expect(screen.queryByText(messages.giris.demo.title)).toBeNull();
  });

  it("fills email and password when an account is picked", async () => {
    render(<LoginForm showDemoAccounts />);
    const account = DEMO_ACCOUNTS[0];
    const label = messages.giris.demo.fillLabel.replace("{role}", messages.giris.demo.roles[account.role]);

    await userEvent.click(screen.getByRole("button", { name: label }));

    expect((screen.getByLabelText(messages.giris.emailLabel) as HTMLInputElement).value).toBe(account.email);
    expect((screen.getByLabelText(messages.giris.passwordLabel) as HTMLInputElement).value).toBe(DEMO_PASSWORD);
  });

  it("admin variant fills only the admin email and never shows a password", async () => {
    render(<LoginForm adminOnly showDemoAccounts />);

    expect(screen.queryByText(messages.giris.demo.title)).toBeNull();
    expect(screen.queryByText(DEMO_PASSWORD)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: messages.giris.demo.adminFillLabel }));

    expect((screen.getByLabelText(messages.giris.emailLabel) as HTMLInputElement).value).toBe(DEMO_ADMIN_EMAIL);
    expect((screen.getByLabelText(messages.giris.passwordLabel) as HTMLInputElement).value).toBe("");
    expect(document.activeElement).toBe(screen.getByLabelText(messages.giris.passwordLabel));
  });

  it("shows the shared demo password when a demo e-mail fails to sign in", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_ACCOUNTS", "1");
    vi.mocked(login).mockRejectedValue({ status: 401, code: "INVALID_CREDENTIALS" });
    render(<LoginForm />);

    await userEvent.type(screen.getByLabelText(messages.giris.emailLabel), DEMO_ACCOUNTS[0].email);
    await userEvent.type(screen.getByLabelText(messages.giris.passwordLabel), "autofilled-other-password");
    await userEvent.click(screen.getByRole("button", { name: messages.giris.login }));

    await waitFor(() => expect(screen.getByText(new RegExp(DEMO_PASSWORD.replace("!", "\!")))).toBeTruthy());
  });

  it("keeps the generic error for a non-demo e-mail", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_ACCOUNTS", "1");
    vi.mocked(login).mockRejectedValue({ status: 401, code: "INVALID_CREDENTIALS" });
    render(<LoginForm />);

    await userEvent.type(screen.getByLabelText(messages.giris.emailLabel), "biri@ornek.test");
    await userEvent.type(screen.getByLabelText(messages.giris.passwordLabel), "yanlis-sifre");
    await userEvent.click(screen.getByRole("button", { name: messages.giris.login }));

    await waitFor(() => expect(screen.getByText(messages.giris.invalidCredentials)).toBeTruthy());
    expect(screen.queryByText(new RegExp(DEMO_PASSWORD.replace("!", "\!")))).toBeNull();
  });

  it("is enabled in development or with NEXT_PUBLIC_DEMO_ACCOUNTS=1 only", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_DEMO_ACCOUNTS", "");
    expect(demoAccountsEnabled()).toBe(false);
    vi.stubEnv("NEXT_PUBLIC_DEMO_ACCOUNTS", "1");
    expect(demoAccountsEnabled()).toBe(true);
    vi.stubEnv("NEXT_PUBLIC_DEMO_ACCOUNTS", "");
    vi.stubEnv("NODE_ENV", "development");
    expect(demoAccountsEnabled()).toBe(true);
  });
});
