import { describe, it, expect } from "vitest";

/**
 * AC-9: Client-side validation schemas (Zod).
 * Tests that form validation rules are properly enforced:
 * - Email format validation
 * - Password minimum length (8 characters)
 * - Full name requirement
 * - Password confirmation matching
 */

// These schemas will be imported from schemas.ts when that file is created
// For now, we define them inline to ensure tests can run (red phase)
// The actual schemas.ts should match these definitions

import { z } from "zod";

// Registro schema
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

// Login schema
export const loginSchema = z.object({
  email: z
    .string()
    .email("Geçerli bir e-posta adresi giriniz"),
  password: z
    .string()
    .min(1, "Şifre gereklidir"),
});

// Forgot password schema
export const forgotPasswordSchema = z.object({
  email: z
    .string()
    .email("Geçerli bir e-posta adresi giriniz"),
});

// Reset password schema with password confirmation
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

describe("registerSchema", () => {
  it("AC-9: accepts valid registration data", () => {
    const data = {
      email: "user@example.com",
      password: "password123",
      full_name: "John Doe",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: rejects invalid email format", () => {
    const data = {
      email: "not-an-email",
      password: "password123",
      full_name: "John Doe",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(false);
    expect(result.error?.errors[0].message).toContain("e-posta");
  });

  it("AC-9: rejects password shorter than 8 characters", () => {
    const data = {
      email: "user@example.com",
      password: "short",
      full_name: "John Doe",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(false);
    expect(result.error?.errors[0].message).toContain("8");
  });

  it("AC-9: rejects empty full_name", () => {
    const data = {
      email: "user@example.com",
      password: "password123",
      full_name: "",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("AC-9: accepts password exactly 8 characters", () => {
    const data = {
      email: "user@example.com",
      password: "12345678",
      full_name: "John Doe",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: accepts password up to 128 characters", () => {
    const data = {
      email: "user@example.com",
      password: "a".repeat(128),
      full_name: "John Doe",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: rejects password longer than 128 characters", () => {
    const data = {
      email: "user@example.com",
      password: "a".repeat(129),
      full_name: "John Doe",
    };
    const result = registerSchema.safeParse(data);
    expect(result.success).toBe(false);
    expect(result.error?.errors[0].message).toContain("128");
  });
});

describe("loginSchema", () => {
  it("AC-9: accepts valid login data", () => {
    const data = {
      email: "user@example.com",
      password: "password123",
    };
    const result = loginSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: rejects invalid email format", () => {
    const data = {
      email: "not-an-email",
      password: "password123",
    };
    const result = loginSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("AC-9: rejects empty password", () => {
    const data = {
      email: "user@example.com",
      password: "",
    };
    const result = loginSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("AC-9: accepts any non-empty password (no minimum for login)", () => {
    const data = {
      email: "user@example.com",
      password: "a",
    };
    const result = loginSchema.safeParse(data);
    expect(result.success).toBe(true);
  });
});

describe("forgotPasswordSchema", () => {
  it("AC-9: accepts valid email", () => {
    const data = {
      email: "user@example.com",
    };
    const result = forgotPasswordSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: rejects invalid email format", () => {
    const data = {
      email: "not-an-email",
    };
    const result = forgotPasswordSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("AC-9: rejects empty email", () => {
    const data = {
      email: "",
    };
    const result = forgotPasswordSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe("resetPasswordSchema", () => {
  it("AC-9: accepts matching passwords", () => {
    const data = {
      new_password: "newpassword123",
      password_confirm: "newpassword123",
    };
    const result = resetPasswordSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: rejects non-matching passwords", () => {
    const data = {
      new_password: "newpassword123",
      password_confirm: "different",
    };
    const result = resetPasswordSchema.safeParse(data);
    expect(result.success).toBe(false);
    expect(result.error?.errors[0].message).toContain("eşleş");
  });

  it("AC-9: rejects password shorter than 8 characters", () => {
    const data = {
      new_password: "short",
      password_confirm: "short",
    };
    const result = resetPasswordSchema.safeParse(data);
    expect(result.success).toBe(false);
    expect(result.error?.errors[0].message).toContain("8");
  });

  it("AC-9: accepts password exactly 8 characters with confirmation", () => {
    const data = {
      new_password: "12345678",
      password_confirm: "12345678",
    };
    const result = resetPasswordSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("AC-9: error message is in Turkish", () => {
    const data = {
      new_password: "password123",
      password_confirm: "different",
    };
    const result = resetPasswordSchema.safeParse(data);
    expect(result.success).toBe(false);
    expect(result.error?.errors[0].message).not.toContain("password");
  });
});
