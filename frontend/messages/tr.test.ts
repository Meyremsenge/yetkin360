import { describe, it, expect } from "vitest";
import messages from "@/messages/tr.json";

/**
 * AC-9: Tüm gerekli Türkçe metinler messages/tr.json'da.
 * Anahtar yolları ve değer kontrolü.
 */

describe("messages/tr.json", () => {
  describe("AC-9: Tüm zorunlu anahtar yolları var", () => {
    const requiredPaths = [
      "home.title",
      "home.tagline",
      "home.cta",
      "shell.loading",
      "shell.noOrganizations",
      "session.expired",
      "session.loadFailed",
      "session.logout",
      "session.logoutFailed",
      "errors.generic",
      "errors.network",
      "errors.timeout",
      "errors.retry",
      "errors.supportCode",
      "errors.emailNotVerified",
      "errors.rateLimited",
      "notFound.title",
      "notFound.home",
      "notFound.login",
      "giris.title",
      "giris.placeholder",
      "giris.emailLabel",
      "giris.passwordLabel",
      "giris.invalidCredentials",
      "giris.accountLocked",
      "kayit.title",
      "kayit.emailLabel",
      "kayit.passwordLabel",
      "kayit.fullNameLabel",
      "kayit.submit",
      "kayit.success",
      "epostaDogrula.verifying",
      "epostaDogrula.success",
      "epostaDogrula.tokenInvalid",
      "sifreUnuttum.title",
      "sifreUnuttum.emailLabel",
      "sifreUnuttum.submit",
      "sifreUnuttum.sentMessage",
      "sifreSifirla.title",
      "sifreSifirla.newPasswordLabel",
      "sifreSifirla.confirmPasswordLabel",
      "sifreSifirla.submit",
      "sifreSifirla.success",
    ];

    it.each(requiredPaths)(
      "AC-9: '%s' anahtar yolu var",
      (path) => {
        const keys = path.split(".");
        let value = messages as any;

        for (const key of keys) {
          expect(value).toHaveProperty(key);
          value = value[key];
        }

        expect(value).toBeDefined();
        expect(typeof value).toBe("string");
        expect(value.length).toBeGreaterThan(0);
      }
    );
  });

  describe("AC-9: Spesifik metin değerleri", () => {
    it("AC-9: home.title metni", () => {
      expect(messages.home.title).toBeDefined();
      expect(typeof messages.home.title).toBe("string");
      expect(messages.home.title.length).toBeGreaterThan(0);
    });

    it("AC-9: home.tagline metni", () => {
      expect(messages.home.tagline).toBeDefined();
      expect(typeof messages.home.tagline).toBe("string");
    });

    it("AC-9: home.cta = 'Başla'", () => {
      expect(messages.home.cta).toBe("Başla");
    });

    it("AC-9: shell.loading metni gözükür", () => {
      expect(messages.shell.loading).toContain("Yükleniyor");
    });

    it("AC-9: session.expired = 'Oturumunuz sona erdi'", () => {
      expect(messages.session.expired).toContain("Oturumunuz sona erdi");
    });

    it("AC-9: errors.retry = 'Tekrar dene'", () => {
      expect(messages.errors.retry).toBe("Tekrar dene");
    });

    it("AC-9: errors.supportCode = 'Destek kodu'", () => {
      expect(messages.errors.supportCode).toBe("Destek kodu");
    });

    it("AC-9: notFound.title", () => {
      expect(messages.notFound.title).toContain("Sayfa bulunamadı");
    });

    it("AC-9: giris.title", () => {
      expect(messages.giris.title).toContain("Giriş");
    });
  });

  describe("AC-9: Türkçe karakterler", () => {
    it("AC-9: session.expired Türkçe karakterler içerir", () => {
      expect(messages.session.expired).toMatch(/[çğıöşüÇĞİÖŞÜ]/);
    });

    it("AC-9: errors.timeout Türkçe metin", () => {
      expect(messages.errors.timeout).toBeDefined();
      expect(messages.errors.timeout.length).toBeGreaterThan(0);
    });

    it("AC-9: shell.noOrganizations Türkçe metin", () => {
      expect(messages.shell.noOrganizations).toBeDefined();
      expect(typeof messages.shell.noOrganizations).toBe("string");
    });
  });

  describe("AC-9: Metin boşluğu kontrolü", () => {
    const messagePaths = [
      ["home", "title"],
      ["home", "tagline"],
      ["home", "cta"],
      ["shell", "loading"],
      ["shell", "noOrganizations"],
      ["session", "expired"],
      ["session", "loadFailed"],
      ["session", "logout"],
      ["session", "logoutFailed"],
      ["errors", "generic"],
      ["errors", "network"],
      ["errors", "timeout"],
      ["errors", "retry"],
      ["errors", "supportCode"],
      ["errors", "emailNotVerified"],
      ["errors", "rateLimited"],
      ["notFound", "title"],
      ["notFound", "home"],
      ["notFound", "login"],
      ["giris", "title"],
      ["giris", "placeholder"],
      ["giris", "emailLabel"],
      ["giris", "passwordLabel"],
      ["giris", "invalidCredentials"],
      ["giris", "accountLocked"],
      ["kayit", "title"],
      ["kayit", "emailLabel"],
      ["kayit", "passwordLabel"],
      ["kayit", "fullNameLabel"],
      ["kayit", "submit"],
      ["kayit", "success"],
      ["epostaDogrula", "verifying"],
      ["epostaDogrula", "success"],
      ["epostaDogrula", "tokenInvalid"],
      ["sifreUnuttum", "title"],
      ["sifreUnuttum", "emailLabel"],
      ["sifreUnuttum", "submit"],
      ["sifreUnuttum", "sentMessage"],
      ["sifreSifirla", "title"],
      ["sifreSifirla", "newPasswordLabel"],
      ["sifreSifirla", "confirmPasswordLabel"],
      ["sifreSifirla", "submit"],
      ["sifreSifirla", "success"],
    ];

    it.each(messagePaths)(
      "AC-9: %s boş string değildir",
      (...keys) => {
        let value = messages as any;
        for (const key of keys) {
          value = value[key];
        }
        expect(typeof value).toBe("string");
        expect(value.trim().length).toBeGreaterThan(0);
      }
    );
  });

  describe("AC-9: JSON yapısı", () => {
    it("AC-9: messages bir object'tir", () => {
      expect(typeof messages).toBe("object");
      expect(messages).not.toBeNull();
    });

    it("AC-9: Ana gruplar var: home, shell, session, errors, notFound, giris, kayit, epostaDogrula, sifreUnuttum, sifreSifirla", () => {
      expect(messages).toHaveProperty("home");
      expect(messages).toHaveProperty("shell");
      expect(messages).toHaveProperty("session");
      expect(messages).toHaveProperty("errors");
      expect(messages).toHaveProperty("notFound");
      expect(messages).toHaveProperty("giris");
      expect(messages).toHaveProperty("kayit");
      expect(messages).toHaveProperty("epostaDogrula");
      expect(messages).toHaveProperty("sifreUnuttum");
      expect(messages).toHaveProperty("sifreSifirla");
    });
  });

  describe("Davranış Sözleşmesi satır 1, 5a, 7a, 7b: Metin kaynakları", () => {
    it("Davranış 1: layout metni messages'tan", () => {
      expect(messages.home.title).toBeDefined();
    });

    it("Davranış 5a: ağ hatası mesajı", () => {
      expect(messages.errors.network).toBeDefined();
    });

    it("Davranış 7a: InvalidResponseError mesajı", () => {
      expect(messages.session.loadFailed).toBeDefined();
    });

    it("Davranış 7b: logout hatası mesajı", () => {
      expect(messages.session.logoutFailed).toBeDefined();
    });
  });
});
