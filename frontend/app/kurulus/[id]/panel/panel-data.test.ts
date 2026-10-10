import { describe, it, expect } from "vitest";
import {
  aggregatePartners,
  groupInbox,
  inboxGroup,
  orgRoleOf,
  rowAction,
  summarize,
  type PanelEngagement,
} from "./panel-data";

function row(id: string, status: string, extra: Partial<PanelEngagement> = {}): PanelEngagement {
  return {
    id,
    talent_id: `t-${id}`,
    talent_name: `Kişi ${id}`,
    title: id,
    kind: "INTERNSHIP",
    status: status as PanelEngagement["status"],
    organization_id: "org-1",
    institution_id: null,
    organization_name: "Acme",
    version: 1,
    updated_at: "2026-10-01T10:00:00Z",
    ...extra,
  };
}

describe("orgRoleOf", () => {
  it("rolü /me'den okur; yoksa MEMBER, üyelik yoksa null", () => {
    expect(orgRoleOf([{ id: "org-1", role: "ADMIN" }], "org-1")).toBe("ADMIN");
    expect(orgRoleOf([{ id: "org-1", role: "MEMBER" }], "org-1")).toBe("MEMBER");
    expect(orgRoleOf([{ id: "org-1" }], "org-1")).toBe("MEMBER");
    expect(orgRoleOf([{ id: "org-2", role: "ADMIN" }], "org-1")).toBeNull();
    expect(orgRoleOf([null, "x"], "org-1")).toBeNull();
    expect(orgRoleOf(undefined, "org-1")).toBeNull();
  });
});

describe("rowAction / inboxGroup", () => {
  it.each([
    ["PENDING_EVALUATION", null, true, "evaluate", "action"],
    ["PENDING_EVALUATION", null, false, "evaluate", "action"],
    ["ACTIVE", null, false, "startEvaluation", "ongoing"],
    ["EVALUATED", null, true, "seal", "action"],
    ["EVALUATED", null, false, null, "ongoing"],
    ["EVALUATED", "inst-1", true, "awaitingUniversitySeal", "ongoing"],
    ["PENDING_APPROVAL", "inst-1", true, null, "ongoing"],
    ["DRAFT", null, true, null, "ongoing"],
    ["VERIFIED", null, true, null, "done"],
    ["RESOLVED", null, true, null, "done"],
    ["REJECTED", null, true, null, null],
    ["CANCELLED", null, true, null, null],
    ["DISPUTED", null, true, null, null],
  ])("%s (kurum=%s, admin=%s) → %s / %s", (status, institution, isAdmin, action, group) => {
    const item = row("x", status, { institution_id: institution });
    expect(rowAction(item, "org-1", isAdmin)).toBe(action);
    expect(inboxGroup(item, "org-1", isAdmin)).toBe(group);
  });

  it("aksiyon grubunda en uzun bekleyen üstte, diğerlerinde en yeni üstte", () => {
    const groups = groupInbox(
      [
        row("new", "PENDING_EVALUATION", { updated_at: "2026-10-05T00:00:00Z" }),
        row("old", "PENDING_EVALUATION", { updated_at: "2026-10-01T00:00:00Z" }),
        row("a1", "ACTIVE", { updated_at: "2026-10-01T00:00:00Z" }),
        row("a2", "ACTIVE", { updated_at: "2026-10-03T00:00:00Z" }),
      ],
      "org-1",
      true
    );
    expect(groups.action.map((i) => i.id)).toEqual(["old", "new"]);
    expect(groups.ongoing.map((i) => i.id)).toEqual(["a2", "a1"]);
  });
});

describe("summarize", () => {
  it("bekleyen (tümü / bana atanan), devam eden, mühürlenen, üniversite sayısı", () => {
    const summary = summarize(
      [
        row("1", "PENDING_EVALUATION", { supervisor_user_id: "me" }),
        row("2", "PENDING_EVALUATION", { supervisor_user_id: "other" }),
        row("3", "ACTIVE", { institution_id: "i1" }),
        row("4", "PENDING_APPROVAL", { institution_id: "i1" }),
        row("5", "VERIFIED", { institution_id: "i2" }),
      ],
      "me"
    );
    expect(summary).toEqual({ awaitingAll: 2, awaitingMine: 1, ongoing: 2, sealed: 1, universities: 2 });
  });

  it("oturum yoksa bana atanan sıfırdır (supervisor alanı eksikken de)", () => {
    expect(summarize([row("1", "PENDING_EVALUATION")], undefined).awaitingMine).toBe(0);
  });
});

describe("aggregatePartners", () => {
  it("kişi tekil sayılır, iptal/red hariç; bireyseller sonda", () => {
    const rows = aggregatePartners([
      row("1", "VERIFIED", { institution_id: "i1", institution_name: "Galata", talent_id: "t1" }),
      row("2", "ACTIVE", { institution_id: "i1", institution_name: "Galata", talent_id: "t1" }),
      row("3", "ACTIVE", { institution_id: "i2", institution_name: "Boğaz", talent_id: "t2" }),
      row("4", "CANCELLED", { institution_id: "i3", institution_name: "Yok", talent_id: "t3" }),
      row("5", "ACTIVE", { talent_id: "t4" }),
    ]);
    expect(rows).toEqual([
      { institutionId: "i2", name: "Boğaz", people: 1, sealed: 0 },
      { institutionId: "i1", name: "Galata", people: 1, sealed: 1 },
      { institutionId: null, name: null, people: 1, sealed: 0 },
    ]);
  });
});
