import { z } from "zod";

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
});

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
