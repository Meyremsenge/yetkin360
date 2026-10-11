import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TaskForm } from "./task-form";
import { createTask } from "@/lib/api/tasks";
import { ApiError } from "@/lib/api/errors";
import type { EngagementDetail } from "@/lib/api/engagements";
import { makeViewer } from "@/lib/api/engagements.fixtures";
import messages from "@/messages/tr.json";

vi.mock("@/lib/api/tasks", () => ({
  createTask: vi.fn(),
}));

vi.mock("@/components/skill-picker", () => ({
  SkillPicker: ({ onChange, label }: { onChange: (id: string | null) => void; label: string }) => (
    <div>
      <span>{label}</span>
      <button type="button" onClick={() => onChange("skill-1")}>
        Mock Skill Seç
      </button>
    </div>
  ),
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

const activeEngagement: EngagementDetail = {
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
  tasks: [],
  deliverables: [],
  attestations: [],
  supervisor: null,
  viewer: makeViewer({ relation: "ORG_ADMIN", can_add_task: true }),
};

describe("TaskForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("ACTIVE durumunda form render edilir", () => {
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    expect(screen.getByLabelText("Başlık")).toBeTruthy();
    expect(screen.getByText("Görev Ekle")).toBeTruthy();
  });

  it("viewer.can_add_task false ise (ör. REJECTED) hiçbir şey render edilmez", () => {
    renderWithQueryClient(
      <TaskForm
        engagement={{ ...activeEngagement, status: "REJECTED", viewer: makeViewer({ relation: "ORG_ADMIN" }) }}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.queryByLabelText("Başlık")).toBeNull();
  });

  it("happy path: başlık girilip gönderilince createTask çağrılır, başarı mesajı gösterilir, onSuccess tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createTask).mockResolvedValueOnce({ id: "task-1", title: "API şeması", status: "PLANNED", verified: true });

    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Başlık"), "API şeması");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => {
      expect(createTask).toHaveBeenCalledWith("eng-1", {
        title: "API şeması",
        description: undefined,
        due_at: undefined,
        skill_id: undefined,
      });
      expect(screen.getByText("Görev eklendi.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("skill seçilirse payload'a skill_id dahil edilir", async () => {
    vi.mocked(createTask).mockResolvedValueOnce({ id: "task-2", title: "Test yazma", status: "PLANNED", verified: true });

    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "Test yazma");
    await user.click(screen.getByText("Mock Skill Seç"));
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => {
      expect(createTask).toHaveBeenCalledWith("eng-1", {
        title: "Test yazma",
        description: undefined,
        due_at: undefined,
        skill_id: "skill-1",
      });
    });
  });

  it("son tarih girilirse ISO string olarak gönderilir", async () => {
    vi.mocked(createTask).mockResolvedValueOnce({ id: "task-3", title: "x", status: "PLANNED", verified: true });

    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.type(screen.getByLabelText("Son Tarih (opsiyonel)"), "2026-11-01");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => {
      expect(createTask).toHaveBeenCalledWith(
        "eng-1",
        expect.objectContaining({ title: "x", due_at: new Date("2026-11-01").toISOString() })
      );
    });
  });

  it("403 FORBIDDEN → yetki hatası mesajı gösterilir", async () => {
    vi.mocked(createTask).mockRejectedValueOnce(
      new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => {
      expect(screen.getByText("Bu işlemi yapma yetkiniz yok.")).toBeTruthy();
    });
  });

  it("422 PRECONDITION_FAILED → 'aktif değil' mesajı gösterilir ve onSuccess (refetch) tetiklenir", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createTask).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "PRECONDITION_FAILED", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => {
      expect(screen.getByText("Görev yalnızca aktif çalışmalara eklenebilir.")).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("422 INVALID_REQUEST → geçersiz yetkinlik mesajı gösterilir", async () => {
    vi.mocked(createTask).mockRejectedValueOnce(
      new ApiError({ status: 422, code: "INVALID_REQUEST", message: "x", requestId: null })
    );

    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => {
      expect(screen.getByText("Seçilen yetkinlik geçersiz.")).toBeTruthy();
    });
  });

  it("başarı mesajı, durum ACTIVE'den çıksa bile bir an görünür kalır (early-return deseni)", async () => {
    const onSuccess = vi.fn();
    vi.mocked(createTask).mockResolvedValueOnce({ id: "task-1", title: "x", status: "PLANNED", verified: true });

    const user = userEvent.setup();
    const { rerender } = renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText("Başlık"), "x");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => expect(screen.getByText("Görev eklendi.")).toBeTruthy());

    rerender(
      <TaskForm
        engagement={{ ...activeEngagement, status: "PENDING_EVALUATION", viewer: makeViewer({ relation: "ORG_ADMIN" }) }}
        onSuccess={onSuccess}
      />
    );
    expect(screen.getByText("Görev eklendi.")).toBeTruthy();
  });

  it("görev varsa form kapalı gelir; 'Görev ekle' açar, Vazgeç kapatır", async () => {
    const withTask = {
      ...activeEngagement,
      tasks: [{ id: "t-1", title: "Var olan", status: "PLANNED", verified: true }],
    } as EngagementDetail;
    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={withTask} onSuccess={vi.fn()} />);

    expect(screen.queryByLabelText("Başlık")).toBeNull();
    await user.click(screen.getByRole("button", { name: messages.calismalar.openTaskForm }));
    expect(document.activeElement).toBe(screen.getByLabelText("Başlık"));

    await user.click(screen.getByRole("button", { name: messages.calismalar.taskCancelButton }));
    expect(screen.queryByLabelText("Başlık")).toBeNull();
  });

  it("ekledikten sonra form açık ve boş kalır, başlığa odaklanır (art arda görev)", async () => {
    vi.mocked(createTask).mockResolvedValueOnce({ id: "task-1", title: "x", status: "PLANNED", verified: true });
    const user = userEvent.setup();
    renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);

    await user.type(screen.getByLabelText("Başlık"), "İlk görev");
    await user.click(screen.getByText("Görev Ekle"));

    await waitFor(() => expect(screen.getByText("Görev eklendi.")).toBeTruthy());
    const titleInput = screen.getByLabelText("Başlık") as HTMLInputElement;
    expect(titleInput.value).toBe("");
    expect(document.activeElement).toBe(titleInput);
  });

  describe("öğrenci (isSubject)", () => {
    const draftEngagement: EngagementDetail = {
      ...activeEngagement,
      status: "DRAFT",
      viewer: makeViewer({ relation: "SUBJECT", can_add_task: true }),
    };

    it("taslak çalışmada formu ve doğrulanmamış uyarısını gösterir", () => {
      renderWithQueryClient(<TaskForm engagement={draftEngagement} onSuccess={vi.fn()} isSubject />);
      expect(screen.getByLabelText("Başlık")).toBeTruthy();
      expect(screen.getByText(messages.calismalar.taskUnverifiedHint)).toBeTruthy();
    });

    it("öğrenci değilse taslak çalışmada form gösterilmez", () => {
      renderWithQueryClient(
        <TaskForm
          engagement={{ ...draftEngagement, viewer: makeViewer({ relation: "ORG_ADMIN" }) }}
          onSuccess={vi.fn()}
        />
      );
      expect(screen.queryByLabelText("Başlık")).toBeNull();
    });

    it("öğrenci değilse aktif çalışmada doğrulanmamış uyarısı gösterilmez", () => {
      renderWithQueryClient(<TaskForm engagement={activeEngagement} onSuccess={vi.fn()} />);
      expect(screen.queryByText(messages.calismalar.taskUnverifiedHint)).toBeNull();
    });

    it("onay bekleyen çalışmada öğrenciye de form gösterilmez", () => {
      renderWithQueryClient(
        <TaskForm
          engagement={{ ...activeEngagement, status: "PENDING_APPROVAL", viewer: makeViewer({ relation: "SUBJECT" }) }}
          onSuccess={vi.fn()}
          isSubject
        />
      );
      expect(screen.queryByLabelText("Başlık")).toBeNull();
    });

    it("görev eklenince doğrulanmamış olduğunu söyleyen mesajı gösterir", async () => {
      vi.mocked(createTask).mockResolvedValueOnce({ id: "task-9", title: "x", status: "PLANNED", verified: false });
      const onSuccess = vi.fn();
      const user = userEvent.setup();
      renderWithQueryClient(<TaskForm engagement={draftEngagement} onSuccess={onSuccess} isSubject />);

      await user.type(screen.getByLabelText("Başlık"), "Kendi görevim");
      await user.click(screen.getByText("Görev Ekle"));

      expect(await screen.findByText(messages.calismalar.taskAddedUnverifiedMessage)).toBeTruthy();
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
