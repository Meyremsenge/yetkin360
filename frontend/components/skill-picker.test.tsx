import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SkillPicker } from "./skill-picker";
import * as clientModule from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  listSkills: vi.fn(),
}));

describe("SkillPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("arama input'una yazılınca debounce sonrası listSkills çağrılır, sonuçlar listelenir", async () => {
    const mockListSkills = vi.spyOn(clientModule, "listSkills");
    mockListSkills.mockResolvedValueOnce({ items: [{ id: "skill-1", name_tr: "Python" }] });

    const onChange = vi.fn();
    render(<SkillPicker value={null} onChange={onChange} label="Yetkinlik" />);

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Yetkinlik ara..."), "Python");

    await waitFor(() => {
      expect(mockListSkills).toHaveBeenCalledWith("Python");
    });

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeTruthy();
    });
  });

  it("bir sonuca tıklanınca onChange(skillId) çağrılır ve seçili etiket gösterilir", async () => {
    const mockListSkills = vi.spyOn(clientModule, "listSkills");
    mockListSkills.mockResolvedValueOnce({ items: [{ id: "skill-1", name_tr: "Python" }] });

    const onChange = vi.fn();
    const { rerender } = render(<SkillPicker value={null} onChange={onChange} label="Yetkinlik" />);

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Yetkinlik ara..."), "Python");

    await waitFor(() => expect(screen.getByText("Python")).toBeTruthy());
    await user.click(screen.getByText("Python"));

    expect(onChange).toHaveBeenCalledWith("skill-1");

    // Seçili durumu göstermek için parent value'yu günceller (gerçek kullanım şekli)
    rerender(<SkillPicker value="skill-1" onChange={onChange} label="Yetkinlik" />);
    await waitFor(() => expect(screen.getByText("Temizle")).toBeTruthy());
  });

  it("'Temizle' butonu onChange(null) çağırır", async () => {
    const onChange = vi.fn();
    const mockListSkills = vi.spyOn(clientModule, "listSkills");
    mockListSkills.mockResolvedValueOnce({ items: [{ id: "skill-1", name_tr: "Python" }] });

    const { rerender } = render(<SkillPicker value={null} onChange={onChange} label="Yetkinlik" />);
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Yetkinlik ara..."), "Python");
    await waitFor(() => expect(screen.getByText("Python")).toBeTruthy());
    await user.click(screen.getByText("Python"));

    rerender(<SkillPicker value="skill-1" onChange={onChange} label="Yetkinlik" />);
    await user.click(screen.getByText("Temizle"));

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("boş arama sorgusu listSkills çağırmaz", async () => {
    const mockListSkills = vi.spyOn(clientModule, "listSkills");
    render(<SkillPicker value={null} onChange={vi.fn()} label="Yetkinlik" />);

    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(mockListSkills).not.toHaveBeenCalled();
  });
});
