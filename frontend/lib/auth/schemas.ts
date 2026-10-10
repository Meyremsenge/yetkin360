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
});

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
