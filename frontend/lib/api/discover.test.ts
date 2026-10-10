import { describe, it, expect, vi, beforeEach } from "vitest";
import { listDiscoverOrganizations, listDiscoverTalents } from "./discover";
import * as client from "./client";
import { ApiError } from "./errors";

vi.mock("./client");

const mockApiFetch = vi.mocked(client.apiFetch);
const emptyPage = { items: [], next_cursor: null, has_more: false };

describe("lib/api/discover", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiFetch.mockResolvedValue(emptyPage);
  });

  describe("listDiscoverTalents", () => {
    it("filtresiz çağrıda GET /discover/talents çağırır", async () => {
      await expect(listDiscoverTalents()).resolves.toEqual(emptyPage);
      expect(mockApiFetch).toHaveBeenCalledWith("/discover/talents");
    });

    it("tüm filtreleri sorgu parametresine çevirir, skill_id'yi tekrarlar", async () => {
      await listDiscoverTalents({
        q: "  ayşe  ",
        skillIds: ["s1", "s2"],
        department: " Hukuk ",
        city: "İzmir",
        cursor: "abc",
      });
      const url = new URL(`http://x${mockApiFetch.mock.calls[0][0]}`);
      expect(url.pathname).toBe("/discover/talents");
      expect(url.searchParams.get("q")).toBe("ayşe");
      expect(url.searchParams.getAll("skill_id")).toEqual(["s1", "s2"]);
      expect(url.searchParams.get("department")).toBe("Hukuk");
      expect(url.searchParams.get("city")).toBe("İzmir");
      expect(url.searchParams.get("cursor")).toBe("abc");
    });

    it("2 karakterden kısa aramayı göndermez (backend 422 döner)", async () => {
      await listDiscoverTalents({ q: "a" });
      expect(mockApiFetch).toHaveBeenCalledWith("/discover/talents");
    });

    it("istemci kapsamı genişleten parametre göndermez", async () => {
      await listDiscoverTalents({ q: "ali", skillIds: ["s1"] });
      const url = new URL(`http://x${mockApiFetch.mock.calls[0][0]}`);
      expect([...url.searchParams.keys()].sort()).toEqual(["q", "skill_id"]);
    });

    it("boş yanıtı hata olarak fırlatır", async () => {
      mockApiFetch.mockResolvedValueOnce(undefined);
      await expect(listDiscoverTalents()).rejects.toBeInstanceOf(ApiError);
    });

    it("API hatasını olduğu gibi iletir", async () => {
      const error = new ApiError({ status: 429, code: "RATE_LIMITED", message: "x", requestId: null });
      mockApiFetch.mockRejectedValueOnce(error);
      await expect(listDiscoverTalents()).rejects.toBe(error);
    });
  });

  describe("listDiscoverOrganizations", () => {
    it("arama ve imleci sorgu parametresine çevirir", async () => {
      await listDiscoverOrganizations({ q: "acme", cursor: "c1" });
      expect(mockApiFetch).toHaveBeenCalledWith("/discover/organizations?q=acme&cursor=c1");
    });

    it("filtresiz çağrıda GET /discover/organizations çağırır", async () => {
      await listDiscoverOrganizations();
      expect(mockApiFetch).toHaveBeenCalledWith("/discover/organizations");
    });

    it("boş yanıtı hata olarak fırlatır", async () => {
      mockApiFetch.mockResolvedValueOnce(undefined);
      await expect(listDiscoverOrganizations()).rejects.toBeInstanceOf(ApiError);
    });
  });
});
