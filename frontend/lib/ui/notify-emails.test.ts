import { describe, it, expect } from "vitest";
import { MAX_NOTIFY_EMAILS, parseNotifyEmails } from "@/lib/ui/notify-emails";

describe("lib/ui/notify-emails", () => {
  it("boş girdi reddedilir: en az bir alıcı zorunlu", () => {
    expect(parseNotifyEmails("")).toEqual({ ok: false, error: "required" });
    expect(parseNotifyEmails("  , ; ")).toEqual({ ok: false, error: "required" });
  });

  it("virgül, noktalı virgül ve boşlukla ayrılan adresleri ayırır", () => {
    expect(parseNotifyEmails(" a@kurum.edu.tr, b@kurum.edu.tr;c@kurum.edu.tr\nd@kurum.edu.tr ")).toEqual({
      ok: true,
      emails: ["a@kurum.edu.tr", "b@kurum.edu.tr", "c@kurum.edu.tr", "d@kurum.edu.tr"],
    });
  });

  it("büyük/küçük harf farkıyla yinelenen adresi bir kez alır", () => {
    expect(parseNotifyEmails("Ayse@kurum.edu.tr, ayse@kurum.edu.tr")).toEqual({
      ok: true,
      emails: ["Ayse@kurum.edu.tr"],
    });
  });

  it("biçimi bozuk adresi adıyla bildirir", () => {
    expect(parseNotifyEmails("a@kurum.edu.tr, koordinator")).toEqual({
      ok: false,
      error: "invalid",
      email: "koordinator",
    });
  });

  it("sınırdan fazla adresi reddeder", () => {
    const many = Array.from({ length: MAX_NOTIFY_EMAILS + 1 }, (_, n) => `k${n}@kurum.edu.tr`).join(", ");
    expect(parseNotifyEmails(many)).toEqual({ ok: false, error: "tooMany" });
  });
});
