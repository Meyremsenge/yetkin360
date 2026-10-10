import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TaskList } from "./task-list";
import { verifyTask } from "@/lib/api/tasks";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/tasks", () => ({
  verifyTask: vi.fn(),
}));

const c = messages.calismalar;

const engagement: EngagementDetail = {
  id: "eng-1",
  title: "Yaz Kısa Projesi",
  kind: "SHORT_PROJECT",
  status: "ACTIVE",
  organization_name: "Bulut Sistemleri Ltd.",
  talent_id: "talent-1",
  organization_id: "org-1",
  institution_id: null,
  reason: null,
  version: 2,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-18T14:30:00Z",
  tasks: [
    { id: "task-1", title: "Kuruluşun görevi", status: "PLANNED", verified: true },
    { id: "task-2", title: "Öğrencinin görevi", status: "PLANNED", verified: false },
  ],
  deliverables: [],
  attestations: [],
};

function renderList(props: { canVerify: boolean; onChange?: () => void }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TaskList engagement={engagement} canVerify={props.canVerify} onChange={props.onChange ?? vi.fn()} />
    </QueryClientProvider>
  );
}

function row(title: string) {
  return screen.getByText(title).closest("li") as HTMLElement;
}

function apiError(status: number, code: string) {
  return new ApiError({ status, code, message: "x", requestId: null });
}

describe("TaskList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("yalnız doğrulanmamış görevde 'Doğrulanmadı' etiketi gösterir", () => {
    renderList({ canVerify: false });
    expect(within(row("Öğrencinin görevi")).getByText(c.taskUnverifiedBadge)).toBeTruthy();
    expect(within(row("Kuruluşun görevi")).queryByText(c.taskUnverifiedBadge)).toBeNull();
  });

  it("öğrenciye (canVerify=false) onay düğmesi göstermez", () => {
    renderList({ canVerify: false });
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("kuruluş/kurum tarafına yalnız doğrulanmamış görevde onay düğmesi gösterir", () => {
    renderList({ canVerify: true });
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(
      within(row("Öğrencinin görevi")).getByRole("button", { name: "Öğrencinin görevi görevini onayla" })
    ).toBeTruthy();
  });

  it("onaylayınca doğrulama ucunu çağırır ve listeyi yeniler", async () => {
    vi.mocked(verifyTask).mockResolvedValueOnce({
      id: "task-2",
      title: "Öğrencinin görevi",
      status: "PLANNED",
      verified: true,
    });
    const onChange = vi.fn();
    renderList({ canVerify: true, onChange });

    await userEvent.setup().click(screen.getByRole("button"));

    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
    expect(verifyTask).toHaveBeenCalledWith("eng-1", "task-2");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("403'te yetki hatası gösterir, listeyi yenilemez", async () => {
    vi.mocked(verifyTask).mockRejectedValueOnce(apiError(403, "FORBIDDEN"));
    const onChange = vi.fn();
    renderList({ canVerify: true, onChange });

    await userEvent.setup().click(screen.getByRole("button"));

    expect((await screen.findByRole("alert")).textContent).toBe(c.taskVerifyForbiddenError);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("görev bu arada onaylanmışsa (409) hata göstermez, listeyi yeniler", async () => {
    vi.mocked(verifyTask).mockRejectedValueOnce(apiError(409, "TASK_ALREADY_VERIFIED"));
    const onChange = vi.fn();
    renderList({ canVerify: true, onChange });

    await userEvent.setup().click(screen.getByRole("button"));

    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("çalışma durumu uygun değilse (422) açıklayıcı hata gösterir", async () => {
    vi.mocked(verifyTask).mockRejectedValueOnce(apiError(422, "PRECONDITION_FAILED"));
    renderList({ canVerify: true });

    await userEvent.setup().click(screen.getByRole("button"));

    expect((await screen.findByRole("alert")).textContent).toBe(c.taskVerifyNotAllowedError);
  });

  it("beklenmeyen hatada genel onay hatası gösterir", async () => {
    vi.mocked(verifyTask).mockRejectedValueOnce(new Error("network"));
    renderList({ canVerify: true });

    await userEvent.setup().click(screen.getByRole("button"));

    expect((await screen.findByRole("alert")).textContent).toBe(c.taskVerifyError);
  });
});
