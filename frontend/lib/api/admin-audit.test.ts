import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "./admin-audit";
import * as client from "./client";
import { ApiError } from "./errors";

vi.mock("./client");
const mockApiFetch = vi.mocked(client.apiFetch);

const empty = { items: [], limit: 50, offset: 0, has_more: false };

describe("admin-audit API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getAuditEvents sends default paging and omits empty filters", async () => {
    mockApiFetch.mockResolvedValue(empty);
    await api.getAuditEvents({ action: "", subject_type: undefined });
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/audit-events?limit=50&offset=0");
  });

  it("getAuditEvents encodes filters and offset", async () => {
    mockApiFetch.mockResolvedValue(empty);
    await api.getAuditEvents({
      action: "ADMIN_SET_VERIFICATION_LEVEL",
      subject_type: "organization",
      actor_user_id: "11111111-1111-1111-1111-111111111111",
      limit: 25,
      offset: 50,
    });
    const url = mockApiFetch.mock.calls[0][0] as string;
    expect(url).toContain("action=ADMIN_SET_VERIFICATION_LEVEL");
    expect(url).toContain("subject_type=organization");
    expect(url).toContain("actor_user_id=11111111-1111-1111-1111-111111111111");
    expect(url).toContain("limit=25");
    expect(url).toContain("offset=50");
  });

  it("getFraudHistory passes status and paging", async () => {
    mockApiFetch.mockResolvedValue(empty);
    await api.getFraudHistory({ status: "DISMISSED", offset: 50 });
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/admin/fraud-flags/history?status=DISMISSED&limit=50&offset=50"
    );
  });

  it("getFraudHistory without status omits it", async () => {
    mockApiFetch.mockResolvedValue(empty);
    await api.getFraudHistory();
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/fraud-flags/history?limit=50&offset=0");
  });

  it("propagates ApiError (non-admin 404)", async () => {
    mockApiFetch.mockRejectedValue(new ApiError({ status: 404, code: "NOT_FOUND", message: "Kaynak bulunamadı.", requestId: null }));
    await expect(api.getAuditEvents()).rejects.toBeInstanceOf(ApiError);
  });
});
