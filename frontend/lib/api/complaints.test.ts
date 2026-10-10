import { describe, it, expect, vi, beforeEach } from "vitest";
import * as client from "./client";
import {
  createComplaint,
  getComplaintEvidenceUrl,
  getComplaintQueue,
  listEngagementComplaints,
  resolveComplaint,
} from "./complaints";
import { ApiError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);

describe("lib/api/complaints", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listEngagementComplaints çalışmanın şikayetlerini döner; boş yanıtta boş liste", async () => {
    mockApiFetch.mockResolvedValueOnce({ items: [{ id: "cmp-1" }] });
    await expect(listEngagementComplaints("eng-1")).resolves.toEqual([{ id: "cmp-1" }]);
    expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/complaints");

    mockApiFetch.mockResolvedValueOnce(undefined);
    await expect(listEngagementComplaints("eng-1")).resolves.toEqual([]);
  });

  it("createComplaint girdiyi POST eder", async () => {
    const input = { category: "PERSONAL" as const, description: "Yirmi karakterden uzun bir açıklama." };
    mockApiFetch.mockResolvedValueOnce({ id: "cmp-1", ...input });

    await createComplaint("eng-1", input);

    expect(mockApiFetch).toHaveBeenCalledWith("/engagements/eng-1/complaints", { method: "POST", body: input });
  });

  it("createComplaint boş yanıtta ApiError fırlatır", async () => {
    mockApiFetch.mockResolvedValueOnce(undefined);

    await expect(
      createComplaint("eng-1", { category: "PERSONAL", description: "Yirmi karakterden uzun bir açıklama." }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("getComplaintQueue durumu sorgu parametresi olarak gönderir", async () => {
    mockApiFetch.mockResolvedValueOnce({ items: [] });

    await getComplaintQueue("UPHELD");

    expect(mockApiFetch).toHaveBeenCalledWith("/admin/complaints?status=UPHELD");
  });

  it("resolveComplaint notu yalnız varsa gönderir", async () => {
    mockApiFetch.mockResolvedValue({ id: "cmp-1" });

    await resolveComplaint("cmp-1", "DISMISSED");
    expect(mockApiFetch).toHaveBeenLastCalledWith("/admin/complaints/cmp-1/resolve", {
      method: "POST",
      body: { outcome: "DISMISSED" },
    });

    await resolveComplaint("cmp-1", "UPHELD", "Kanıt yeterli.");
    expect(mockApiFetch).toHaveBeenLastCalledWith("/admin/complaints/cmp-1/resolve", {
      method: "POST",
      body: { outcome: "UPHELD", note: "Kanıt yeterli." },
    });
  });

  it("getComplaintEvidenceUrl şikayetin belge bağlantısını döner", async () => {
    mockApiFetch.mockResolvedValueOnce({ download_url: "https://storage.example.test/x", expires_in: 300 });

    await expect(getComplaintEvidenceUrl("cmp-1")).resolves.toBe("https://storage.example.test/x");
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/complaints/cmp-1/evidence-url");
  });
});
