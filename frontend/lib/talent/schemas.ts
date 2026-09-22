import { z } from "zod";

/**
 * AC-1/AC-2/AC-3: Talent profile schema for updating profile fields.
 * All fields are optional for partial updates (PATCH body).
 * Fields accept null/undefined for partial updates.
 * visibility is an enum: PRIVATE | INSTITUTION | ORGANIZATIONS | PUBLIC
 */
export const talentProfileSchema = z.object({
  headline: z
    .string()
    .max(255, "Başlık maksimum 255 karakter olmalıdır")
    .nullish(),
  department: z
    .string()
    .max(100, "Bölüm maksimum 100 karakter olmalıdır")
    .nullish(),
  study_year: z
    .number()
    .nullish(),
  city: z
    .string()
    .max(100, "Şehir maksimum 100 karakter olmalıdır")
    .nullish(),
  visibility: z
    .enum(["PRIVATE", "INSTITUTION", "ORGANIZATIONS", "PUBLIC"], {
      errorMap: () => ({ message: "Geçerli bir görünürlük seviyesi seçiniz" }),
    })
    .nullish(),
  public_slug: z
    .string()
    .max(100, "Profil linki maksimum 100 karakter olmalıdır")
    .nullish(),
});

export type TalentProfileFormData = z.infer<typeof talentProfileSchema>;
