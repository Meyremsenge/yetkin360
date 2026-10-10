import { describe, it, expect, vi, beforeEach } from "vitest";
import * as dir from "./admin-directory";
import * as client from "./client";
import { ApiError } from "./errors";

vi.mock("./client");
const mockApiFetch = vi.mocked(client.apiFetch);

const page = { items: [], limit: 50, offset: 0, has_more: false };

describe("admin-directory API client", () => {
  beforeEach(() => vi.resetAllMocks());

  it("listUsers sends default limit/offset and trims q", async () => {
    mockApiFetch.mockResolvedValue(page);
    await dir.listUsers({ q: "  ali@x.com ", status: "SUSPENDED" });
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/users?q=ali%40x.com&status=SUSPENDED&limit=50&offset=0");
  });

  it("listOrganizations omits empty filters and passes offset", async () => {
    mockApiFetch.mockResolvedValue(page);
    await dir.listOrganizations({ q: "", verification_level: "T2", offset: 50 });
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/organizations?verification_level=T2&limit=50&offset=50");
  });

  it("listInstitutions returns the envelope", async () => {
    mockApiFetch.mockResolvedValue({ ...page, has_more: true });
    await expect(dir.listInstitutions()).resolves.toEqual({ ...page, has_more: true });
  });

  it("setSuspended posts to suspend / reactivate", async () => {
    mockApiFetch.mockResolvedValue({ id: "u1", status: "SUSPENDED" });
    await dir.setSuspended("users", "u1", true);
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/users/u1/suspend", { method: "POST", body: {} });
    await dir.setSuspended("organizations", "o1", false);
    expect(mockApiFetch).toHaveBeenLastCalledWith("/admin/organizations/o1/reactivate", { method: "POST", body: {} });
  });

  it("setInstitutionVerificationLevel posts the level", async () => {
    mockApiFetch.mockResolvedValue({ id: "i1", verification_level: "T3" });
    await dir.setInstitutionVerificationLevel("i1", "T3");
    expect(mockApiFetch).toHaveBeenCalledWith("/admin/institutions/i1/verification-level", {
      method: "POST",
      body: { verification_level: "T3" },
    });
  });

  it("propagates 409 LAST_ADMIN_PROTECTED", async () => {
    mockApiFetch.mockRejectedValue(
      new ApiError({ status: 409, code: "LAST_ADMIN_PROTECTED", message: "x", requestId: null })
    );
    await expect(dir.setSuspended("users", "me", true)).rejects.toMatchObject({ code: "LAST_ADMIN_PROTECTED" });
  });
});
