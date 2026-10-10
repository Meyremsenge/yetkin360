import { describe, it, expect } from "vitest";
import {
  isFreeEmailAddress,
  isValidMersis,
  requireCorporateEmailForOrganization,
  requireValidMersisWhenGiven,
} from "@/lib/auth/schemas";

/**
 * Kuruluş kaydı kuralları: kurumsal e-posta ve MERSİS biçimi. Asıl kontrol
 * sunucudadır (POST /auth/register); bunlar formun erken geri bildirimidir.
 */
describe("isFreeEmailAddress", () => {
  it.each(["a@gmail.com", "a@HOTMAIL.com", "a@mail.gmail.com", "a@yandex.com.tr", " a@outlook.com "])(
    "ücretsiz sağlayıcıyı tanır: %s",
    (email) => {
      expect(isFreeEmailAddress(email)).toBe(true);
    }
  );

  it.each(["a@firma.com.tr", "a@notgmail.com", "a@gmail.com.firma.example", "a@uni.edu.tr"])(
    "kurumsal/benzer alan adını ücretsiz saymaz: %s",
    (email) => {
      expect(isFreeEmailAddress(email)).toBe(false);
    }
  );
});

describe("isValidMersis", () => {
  it("16 haneyi kabul eder", () => {
    expect(isValidMersis("0123456789012345")).toBe(true);
  });

  it.each(["", "123", "012345678901234", "01234567890123456", "012345678901234X", "0123 4567 8901 2345"])(
    "16 hane olmayanı reddeder: %s",
    (value) => {
      expect(isValidMersis(value)).toBe(false);
    }
  );
});

describe("form kuralları", () => {
  it("ücretsiz e-posta yalnız ORGANIZATION için engellenir", () => {
    expect(requireCorporateEmailForOrganization({ account_kind: "ORGANIZATION", email: "a@gmail.com" })).toBe(false);
    expect(requireCorporateEmailForOrganization({ account_kind: "ORGANIZATION", email: "a@firma.com.tr" })).toBe(true);
    expect(requireCorporateEmailForOrganization({ account_kind: "TALENT", email: "a@gmail.com" })).toBe(true);
    expect(requireCorporateEmailForOrganization({ account_kind: "INSTITUTION", email: "a@gmail.com" })).toBe(true);
  });

  it("MERSİS boşsa geçer, girildiyse 16 hane olmalıdır", () => {
    expect(requireValidMersisWhenGiven({ account_kind: "ORGANIZATION" })).toBe(true);
    expect(requireValidMersisWhenGiven({ account_kind: "ORGANIZATION", legal_id: "  " })).toBe(true);
    expect(requireValidMersisWhenGiven({ account_kind: "ORGANIZATION", legal_id: "123" })).toBe(false);
    expect(requireValidMersisWhenGiven({ account_kind: "ORGANIZATION", legal_id: " 0123456789012345 " })).toBe(true);
    expect(requireValidMersisWhenGiven({ account_kind: "TALENT", legal_id: "123" })).toBe(true);
  });
});
