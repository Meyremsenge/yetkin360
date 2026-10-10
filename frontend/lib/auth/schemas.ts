import { z } from "zod";

export const accountKinds = ["TALENT", "ORGANIZATION", "INSTITUTION"] as const;
export type AccountKind = (typeof accountKinds)[number];

// Düz ZodObject olarak kalır (refine zincirlenmez) ki form.tsx .extend() ile
// password_confirm ekleyebilsin — tüm .refine() kontrolleri (entity_name
// zorunluluğu dahil) extend edilmiş son şemada birlikte uygulanır.
export const registerSchema = z.object({
  email: z
    .string()
    .email("Geçerli bir e-posta adresi giriniz"),
  password: z
    .string()
    .min(8, "Şifre en az 8 karakter olmalıdır")
    .max(128, "Şifre maksimum 128 karakter olmalıdır"),
  full_name: z
    .string()
    .min(1, "Ad soyad gereklidir"),
  account_kind: z.enum(accountKinds).default("TALENT"),
  entity_name: z.string().max(200).optional(),
  // MERSİS numarası — yalnız ORGANIZATION için gönderilir (backend: organizations.legal_id).
  legal_id: z.string().optional(),
});

// backend/app/services/organization.py FREE_EMAIL_DOMAINS ile aynı liste —
// asıl kontrol sunucudadır (POST /auth/register 422), bu yalnız erken geri bildirim.
const FREE_EMAIL_DOMAINS = [
  "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yandex.com", "icloud.com",
  "hotmail.com.tr", "outlook.com.tr", "protonmail.com", "mail.ru", "yahoo.com.tr",
  "googlemail.com", "live.com", "msn.com", "hotmail.co.uk", "hotmail.de", "hotmail.fr",
  "outlook.de", "yahoo.co.uk", "yahoo.de", "yahoo.fr", "ymail.com", "rocketmail.com",
  "gmx.com", "gmx.net", "gmx.de", "gmx.at", "gmx.ch", "aol.com", "mail.com", "proton.me",
  "pm.me", "tutanota.com", "zoho.com", "yandex.ru", "yandex.com.tr", "mynet.com",
];

/** Listedeki bir sağlayıcı veya alt alan adı (mail.gmail.com) ise true; benzerleri (notgmail.com) değil. */
export function isFreeEmailAddress(email: string): boolean {
  const domain = email.trim().toLowerCase().split("@").pop() ?? "";
  return FREE_EMAIL_DOMAINS.some((free) => domain === free || domain.endsWith(`.${free}`));
}

/** MERSİS numarası 16 hanedir. Yalnız biçim kontrolü — şirketin gerçekliğini kanıtlamaz. */
export function isValidMersis(value: string): boolean {
  return /^\d{16}$/.test(value);
}

export function requireCorporateEmailForOrganization<T extends { account_kind: AccountKind; email: string }>(
  data: T
): boolean {
  return data.account_kind !== "ORGANIZATION" || !isFreeEmailAddress(data.email);
}

export function requireValidMersisWhenGiven<T extends { account_kind: AccountKind; legal_id?: string }>(
  data: T
): boolean {
  return data.account_kind !== "ORGANIZATION" || !data.legal_id?.trim() || isValidMersis(data.legal_id.trim());
}

export function requireEntityNameForNonTalent<T extends { account_kind: AccountKind; entity_name?: string }>(
  data: T
): boolean {
  return data.account_kind === "TALENT" || Boolean(data.entity_name?.trim());
}

export const loginSchema = z.object({
  email: z
    .string()
    .email("Geçerli bir e-posta adresi giriniz"),
  password: z
    .string()
    .min(1, "Şifre gereklidir"),
});

export const forgotPasswordSchema = z.object({
  email: z
    .string()
    .email("Geçerli bir e-posta adresi giriniz"),
});

export const resetPasswordSchema = z
  .object({
    new_password: z
      .string()
      .min(8, "Şifre en az 8 karakter olmalıdır"),
    password_confirm: z
      .string(),
  })
  .refine(
    (data) => data.new_password === data.password_confirm,
    {
      message: "Şifreler eşleşmiyor",
      path: ["password_confirm"],
    }
  );

export type RegisterFormData = z.infer<typeof registerSchema>;
export type LoginFormData = z.infer<typeof loginSchema>;
export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;
