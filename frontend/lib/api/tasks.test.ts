import { describe, it, expect, vi, beforeEach } from "vitest";
import { createTask, verifyTask } from "./tasks";
import * as client from "./client";
import { ApiError, NetworkError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

describe("lib/api/tasks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createTask", () => {
    it("happy path - POST /engagements/{id}/tasks çağırır, 201 döner", async () => {
      const response = { id: "task-1", title: "API şeması", status: "PLANNED", verified: true };
      mockApiFetch.mockResolvedValueOnce(response);

      const result = await createTask("eng-1", { title: "API şeması" });

      expect(result).toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/tasks", {
        method: "POST",
        body: { title: "API şeması" },
      });
    });

    it("opsiyonel alanlarla (description, due_at, skill_id) çağrılabilir", async () => {
      const response = { id: "task-2", title: "Test yazma", status: "PLANNED", verified: true };
      mockApiFetch.mockResolvedValueOnce(response);

      await createTask("eng-1", {
        title: "Test yazma",
        description: "Unit testler",
        due_at: "2026-11-01T00:00:00Z",
        skill_id: "skill-1",
      });

      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/tasks", {
        method: "POST",
        body: {
          title: "Test yazma",
          description: "Unit testler",
          due_at: "2026-11-01T00:00:00Z",
          skill_id: "skill-1",
        },
      });
    });

    it("403 FORBIDDEN - TALENT görev oluşturamaz", async () => {
      const error = new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createTask("eng-1", { title: "x" })).rejects.toMatchObject({ status: 403 });
    });

    it("422 PRECONDITION_FAILED - engagement ACTIVE değilse ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "PRECONDITION_FAILED", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createTask("eng-1", { title: "x" })).rejects.toMatchObject({ code: "PRECONDITION_FAILED" });
    });

    it("422 INVALID_REQUEST - geçersiz skill_id için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 422, code: "INVALID_REQUEST", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createTask("eng-1", { title: "x", skill_id: "bad" })).rejects.toMatchObject({ code: "INVALID_REQUEST" });
    });

    it("404 NOT_FOUND - kapsam dışı engagement için ApiError fırlatır", async () => {
      const error = new ApiError({ status: 404, code: "NOT_FOUND", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);

      await expect(createTask("eng-missing", { title: "x" })).rejects.toMatchObject({ status: 404 });
    });

    it("network error - NetworkError fırlatır", async () => {
      mockApiFetch.mockRejectedValueOnce(new NetworkError("network"));

      await expect(createTask("eng-1", { title: "x" })).rejects.toBeInstanceOf(NetworkError);
    });
  });

  describe("verifyTask", () => {
    it("POST /engagements/{id}/tasks/{taskId}/verify çağırır", async () => {
      const response = { id: "task-1", title: "Görev", status: "PLANNED", verified: true };
      mockApiFetch.mockResolvedValueOnce(response);

      await expect(verifyTask("eng-1", "task-1")).resolves.toEqual(response);
      expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/tasks/task-1/verify", { method: "POST" });
    });

    it("403 FORBIDDEN - öğrenci kendi görevini onaylayamaz", async () => {
      const error = new ApiError({ status: 403, code: "FORBIDDEN", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);
      await expect(verifyTask("eng-1", "task-1")).rejects.toBe(error);
    });

    it("boş yanıtı hata olarak fırlatır", async () => {
      mockApiFetch.mockResolvedValueOnce(undefined);
      await expect(verifyTask("eng-1", "task-1")).rejects.toBeInstanceOf(ApiError);
    });
  });
});
