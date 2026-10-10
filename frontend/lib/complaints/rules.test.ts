import { describe, it, expect } from "vitest";
import {
  complaintFormSchema,
  validateAttachment,
  transitionSchema,
  allowedActions,
  actionRequiresReason,
  isUpheldBadgeVisible,
  MAX_ATTACHMENTS,
} from "./rules";
import { formatDate } from "./format";

describe("complaintFormSchema", () => {
  it("rejects a too-short description and accepts a normal one", () => {
    expect(complaintFormSchema.safeParse({ description: "kısa" }).success).toBe(false);
    expect(complaintFormSchema.safeParse({ description: "Başvurum iki haftadır yanıtsız." }).success).toBe(true);
  });
  it("rejects over-long descriptions", () => {
    expect(complaintFormSchema.safeParse({ description: "a".repeat(2001) }).success).toBe(false);
  });
});

describe("validateAttachment", () => {
  const mk = (type: string, size: number) => ({ type, size, name: "f" }) as File;
  it("accepts pdf/jpeg/png within 10 MB", () => {
    expect(validateAttachment(mk("application/pdf", 1000))).toBeNull();
    expect(validateAttachment(mk("image/png", 1000))).toBeNull();
    expect(validateAttachment(mk("image/jpeg", 10 * 1024 * 1024))).toBeNull();
  });
  it("rejects other types and oversize files", () => {
    expect(validateAttachment(mk("application/x-msdownload", 10))).toBe("fileType");
    expect(validateAttachment(mk("application/pdf", 10 * 1024 * 1024 + 1))).toBe("fileSize");
  });
  it("exposes the 5 attachment cap", () => expect(MAX_ATTACHMENTS).toBe(5));
});

describe("transitions", () => {
  it("requires a reason for DISMISS, REJECT_EXPLANATION, RESOLVE and UPHOLD", () => {
    for (const a of ["DISMISS", "REJECT_EXPLANATION", "RESOLVE", "UPHOLD"] as const) {
      expect(actionRequiresReason(a)).toBe(true);
      expect(transitionSchema(a).safeParse({ text: "  " }).success).toBe(false);
      expect(transitionSchema(a).safeParse({ text: "Gerekçe" }).success).toBe(true);
    }
  });
  it("does not require text for ACCEPT_EXPLANATION", () => {
    expect(transitionSchema("ACCEPT_EXPLANATION").safeParse({ text: "" }).success).toBe(true);
  });
  it("maps statuses to the actions the UI offers", () => {
    expect(allowedActions("ESCALATED")).toEqual(["RESOLVE", "UPHOLD"]);
    expect(allowedActions("EXPLANATION_SUBMITTED")).toEqual(["ACCEPT_EXPLANATION", "REJECT_EXPLANATION"]);
    expect(allowedActions("UPHELD")).toEqual([]);
    expect(allowedActions(null)).toEqual([]);
    expect(allowedActions("UNDER_REVIEW")).toContain("DISMISS");
  });
});

describe("isUpheldBadgeVisible", () => {
  it("is true only for positive finite numbers", () => {
    expect(isUpheldBadgeVisible(3)).toBe(true);
    for (const v of [0, -1, null, undefined, Number.NaN, "3" as unknown as number]) {
      expect(isUpheldBadgeVisible(v)).toBe(false);
    }
  });
});

describe("formatDate", () => {
  it("returns empty string for null / invalid input", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate(undefined)).toBe("");
    expect(formatDate("not-a-date")).toBe("");
    expect(formatDate("2026-10-01T10:00:00Z")).not.toBe("");
  });
});
