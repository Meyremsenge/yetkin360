import { describe, it, expect } from "vitest";
import { sanitizeNext } from "@/lib/auth/sanitize-next";

/**
 * AC-S3: Open redirect prevention.
 * Given `/giris?next=<değer>`, when `next` is tampered with (external URL, protocol, backslash),
 * then yalnız single-slash-prefixed relative paths accepted; everything else → `/`.
 */
describe("sanitizeNext", () => {
  it("AC-S3: accepts valid single-slash relative paths", () => {
    expect(sanitizeNext("/profil")).toBe("/profil");
    expect(sanitizeNext("/kayit/adim-1")).toBe("/kayit/adim-1");
    expect(sanitizeNext("/yetkinlikler/abc")).toBe("/yetkinlikler/abc");
  });

  it("AC-S3: rejects double-slash open redirect (//evil.com)", () => {
    expect(sanitizeNext("//evil.com")).toBe("/");
  });

  it("AC-S3: rejects protocol-based open redirect (https://evil.com)", () => {
    expect(sanitizeNext("https://evil.com")).toBe("/");
    expect(sanitizeNext("http://localhost:3000")).toBe("/");
  });

  it("AC-S3: rejects backslash-based bypass (/\\evil.com)", () => {
    expect(sanitizeNext("/\\evil.com")).toBe("/");
  });

  it("AC-S3: rejects javascript: protocol", () => {
    expect(sanitizeNext("javascript:alert(1)")).toBe("/");
  });

  it("AC-S3: rejects relative-without-leading-slash (no leading /)", () => {
    expect(sanitizeNext("evil.com")).toBe("/");
    expect(sanitizeNext("../profil")).toBe("/");
    expect(sanitizeNext("profil")).toBe("/");
  });

  it("AC-S3: rejects leading slash followed by backslash (/\\ prefix)", () => {
    expect(sanitizeNext("/\\tevil")).toBe("/");
  });

  it("AC-S3: rejects control characters", () => {
    expect(sanitizeNext("/profil\n")).toBe("/");
    expect(sanitizeNext("/profil\r")).toBe("/");
    expect(sanitizeNext("/profil\t")).toBe("/");
    expect(sanitizeNext("/\x00profil")).toBe("/");
  });

  it("AC-S3: handles null and undefined → `/`", () => {
    expect(sanitizeNext(null)).toBe("/");
    expect(sanitizeNext(undefined)).toBe("/");
  });

  it("AC-S3: handles empty string → `/`", () => {
    expect(sanitizeNext("")).toBe("/");
  });

  it("AC-S3: handles root path `/` → `/`", () => {
    expect(sanitizeNext("/")).toBe("/");
  });

  it("AC-S3: rejects single backslash", () => {
    expect(sanitizeNext("\\")).toBe("/");
  });
});
