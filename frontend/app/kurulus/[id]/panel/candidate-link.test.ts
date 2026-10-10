import { describe, it, expect } from "vitest";
import { candidateHref, parseCandidateLink } from "./candidate-link";

describe("parseCandidateLink (AC-4)", () => {
  it.each([
    ["https://yetkin360.org/v/abc_DEF-123", { kind: "verification", token: "abc_DEF-123" }],
    ["http://localhost:3000/v/tok", { kind: "verification", token: "tok" }],
    ["yetkin360.org/p/ayse-yilmaz", { kind: "profile", slug: "ayse-yilmaz" }],
    ["/p/ayse-yilmaz/", { kind: "profile", slug: "ayse-yilmaz" }],
    ["  https://x.example/v/tok?utm=cv#top  ", { kind: "verification", token: "tok" }],
  ])("%s kabul edilir", (input, expected) => {
    expect(parseCandidateLink(input)).toEqual(expected);
  });

  it("başka host'tan gelen bağlantıda yalnız yol alınır", () => {
    const link = parseCandidateLink("https://yetkin360-dogrula.evil.example/v/tok123");
    expect(link).toEqual({ kind: "verification", token: "tok123" });
    expect(candidateHref(link!)).toBe("/v/tok123");
  });

  it.each([
    "",
    "   ",
    "javascript:alert(1)",
    "javascript://yetkin360.org/v/tok",
    "data:text/html,<script>alert(1)</script>",
    "https://yetkin360.org/",
    "https://yetkin360.org/v/",
    "https://yetkin360.org/v/a/b",
    "https://yetkin360.org/x/tok",
    "https://yetkin360.org/v/%2F%2Fevil.example",
    "https://yetkin360.org/v/..",
    "https://yetkin360.org/v/%E0%A4%A",
    "//evil.example/v/tok",
    "rastgele metin",
  ])("%s reddedilir", (input) => {
    expect(parseCandidateLink(input)).toBeNull();
  });

  it("açılacak yol her zaman kendi origin'imizde göreli yoldur", () => {
    expect(candidateHref({ kind: "verification", token: "abc" })).toBe("/v/abc");
    expect(candidateHref({ kind: "profile", slug: "ayse" })).toBe("/p/ayse");
  });
});
