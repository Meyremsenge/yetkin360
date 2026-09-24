import { z } from "zod";

/**
 * PLAN 2.13 (YET-75/100/101): Kurum tarafı değerlendirme formu şeması.
 * Sözleşme: docs/API.md §2.8 (POST /engagements/{id}/evaluation).
 *
 * D8 (docs/DOMAIN.md): NOT_OBSERVED geçerli bir cevaptır, boş değil — şemada
 * diğer üçüyle birebir eşit bir enum değeri, "opsiyonel" ya da varsayılan değil.
 */

export const evaluationRatingSchema = z.enum(["BELOW", "MEETS", "EXCEEDS", "NOT_OBSERVED"]);

export const evaluationItemSchema = z.object({
  criterion: z.string().min(1, "Kriter adı gereklidir").max(255),
  rating: evaluationRatingSchema,
  comment: z.string().max(1000).optional(),
});

export const evaluationFormSchema = z.object({
  items: z.array(evaluationItemSchema).min(1, "En az bir değerlendirme kriteri eklenmelidir"),
  // D9: private_note sadece kurum içinde görünür, öğrenciye asla dönmez.
  private_note: z.string().max(2000).optional(),
});

export type EvaluationRating = z.infer<typeof evaluationRatingSchema>;
export type EvaluationItemFormData = z.infer<typeof evaluationItemSchema>;
export type EvaluationFormData = z.infer<typeof evaluationFormSchema>;
