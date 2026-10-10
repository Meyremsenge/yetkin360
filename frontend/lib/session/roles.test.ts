import { describe, it, expect } from "vitest";
import { homePathFor, isOrgSide } from "./roles";

const base = { user: { id: "u" }, organizations: [], institutions: [] };
const org = { id: "o1", name: "Lale", role: "ADMIN" as const, unit: null };
const inst = { id: "i1", name: "Galata", role: "COORDINATOR" as const };

describe("roles", () => {
  it("isOrgSide: üyelik yoksa false, kuruluş veya kurum varsa true", () => {
    expect(isOrgSide(base)).toBe(false);
    expect(isOrgSide(null)).toBe(false);
    expect(isOrgSide({ ...base, organizations: [org] })).toBe(true);
    expect(isOrgSide({ ...base, institutions: [inst] })).toBe(true);
  });

  it("homePathFor: admin kuyruğu, kuruluş paneli, kurum paneli, bireysel", () => {
    expect(homePathFor({ ...base, user: { id: "u", is_platform_admin: true } })).toBe("/admin/dogrulama-kuyrugu");
    expect(homePathFor({ ...base, organizations: [org], institutions: [inst] })).toBe(
      "/kurulus/o1/panel"
    );
    expect(homePathFor({ ...base, institutions: [inst] })).toBe("/kurum/i1/panel");
    expect(homePathFor(base)).toBe("/calismalar");
    expect(homePathFor(null)).toBe("/calismalar");
  });
});
