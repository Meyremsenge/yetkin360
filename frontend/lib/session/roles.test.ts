import { describe, it, expect } from "vitest";
import { homePathFor, isOrgSide } from "./roles";

const base = { user: { id: "u" }, organizations: [], institutions: [] };

describe("roles", () => {
  it("isOrgSide: üyelik yoksa false, kuruluş veya kurum varsa true", () => {
    expect(isOrgSide(base)).toBe(false);
    expect(isOrgSide(null)).toBe(false);
    expect(isOrgSide({ ...base, organizations: [{ id: "o1" }] })).toBe(true);
    expect(isOrgSide({ ...base, institutions: [{ id: "i1" }] })).toBe(true);
  });

  it("homePathFor: admin kuyruğu, kuruluş paneli, kurum paneli, bireysel", () => {
    expect(homePathFor({ ...base, user: { id: "u", is_platform_admin: true } })).toBe("/admin/dogrulama-kuyrugu");
    expect(homePathFor({ ...base, organizations: [{ id: "o1" }], institutions: [{ id: "i1" }] })).toBe(
      "/kurulus/o1/panel"
    );
    expect(homePathFor({ ...base, institutions: [{ id: "i1" }] })).toBe("/kurum/i1/panel");
    expect(homePathFor(base)).toBe("/calismalar");
    expect(homePathFor(null)).toBe("/calismalar");
  });
});
