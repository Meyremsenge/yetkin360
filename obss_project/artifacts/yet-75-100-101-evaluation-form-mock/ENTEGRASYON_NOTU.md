# Entegrasyon Notu — YET-75/100/101 (PLAN 2.13) Değerlendirme Formu Frontend

**Durum: Backend'de bu uç hiç yok, mock veriyle geliştirildi. Tam entegre DEĞİL.**

Jira'da bana atanmıştı: YET-75 (→ YET-100/101), PLAN 2.13 ("Frontend: değerlendirme
formu — kurum tarafı").

## Backend uçunun durumu

`POST /engagements/{id}/evaluation` — ❌ **backend'de hiç yok.** PLAN.md madde 2.7
("Değerlendirme formu şeması") henüz yazılmadı; 2.9 notu da bunu doğruluyor:
"EVALUATION kaynağı hâlâ açık (YET-71, @be2/Meyrem, 2.6/2.7/2.8'e bağımlı)."

**İyi haber:** Sözleşme zaten `docs/API.md` §2.8'de tam olarak tanımlı (PLAN.md'nin
kendi "Sözleşme önce kuralı" — backend bitmeden `@fe` sözleşmeyle ilerler). Mock, bu
dokümante edilmiş sözleşmeye birebir uyuyor:

- `direction`, `items[]` (`criterion`, `rating`, `comment?`), `private_note?`
- `rating` ∈ `BELOW`/`MEETS`/`EXCEEDS`/`NOT_OBSERVED` (D8 — dördü de eşit, birinci sınıf)
- `private_note` hiçbir okuma ucunda dönmez (D9) — mock'ta da `submitEvaluation()`'ın
  döndürdüğü `EvaluationRecord` tipinde bu alan **yok**, sadece store'a yazılıyor.
- Hatalar: `409 ALREADY_SUBMITTED`, `422 INVALID_STATUS` — sözleşmeyle birebir.

## Bilinçli kapsam kararları

1. **`items[].skill_id` için yetkinlik seçici UI'ı eklenmedi.** Ticket metni sadece
   "items[], rating" diyor; mock'ta her item'ın `skill_id`'si `null` (serbest metin
   kriter). Gerçek entegrasyonda istenirse `listSkills()` (zaten var, `lib/api/client.ts`)
   ile bir seçici eklenebilir — ayrı bir iterasyon.
2. **Engagement durumu otomatik değiştirilmiyor.** `docs/STATE_MACHINE.md` T7'yi
   (`PENDING_EVALUATION → EVALUATED`, otomatik) dokümanın kendisi **AÇIK SORU** olarak
   işaretlemiş: tek yön (`ORG_TO_TALENT`) mü yeterli, yoksa karşılıklı değerlendirme de
   mi bekleniyor? Bu netleşmeden frontend'in bir varsayımla durumu değiştirmesi hatalı
   olurdu — mock sadece kaydı tutuyor, `engagement.status` `PENDING_EVALUATION` kalıyor.
3. **`EVALUATED`/`VERIFIED` durumları frontend'in `EngagementStatus` tipinde yok** —
   çünkü backend'in durum makinesi (`backend/app/services/engagement.py`) da bunları
   henüz implemente etmedi (sadece dokümante edilmiş, PLAN 2.8/2.10 bekliyor).

## Ne yapıldı

- `frontend/lib/evaluation/schemas.ts` — Zod şeması (`evaluationFormSchema`).
- `frontend/lib/api/evaluation.ts` — `submitEvaluation()` (409/422 simülasyonu,
  `getEngagement()`'a bakarak durum kontrolü yapıyor), `hasSubmittedEvaluation()`.
  Store `localStorage` (`yetkin360_mock_evaluations_v1`).
- `frontend/app/calismalar/[id]/degerlendirme/` — form sayfası + `evaluation-form.tsx`
  (React Hook Form + Zod, dinamik `items[]` listesi — `useFieldArray`).
- Engagement detay sayfasında (`/calismalar/[id]`), durum `PENDING_EVALUATION` ise
  "Değerlendirme Formu" linki eklendi.
- **Manuel test edilebilirlik için** `lib/api/engagements.ts`'e 5. bir seed engagement
  eklendi: `mock-eng-5` ("Kısa Süreli Tasarım Danışmanlığı"), doğrudan
  `PENDING_EVALUATION` durumunda — böylece test için önce başka bir engagement'ı
  bu duruma taşımaya gerek yok.

## Backend PLAN 2.7 tamamlandığında yapılacaklar

1. `lib/api/evaluation.ts`'teki `submitEvaluation()`'ı gerçek
   `apiFetch("/engagements/{id}/evaluation", {method:"POST", body})` çağrısına çevir.
2. `localStorage` mock store'unu (`EVALUATION_STORAGE_KEY`, `loadStore`, `saveStore`)
   ve `hasSubmittedEvaluation()`'ın mock implementasyonunu sil — backend zaten
   `409 ALREADY_SUBMITTED`'ı UNIQUE kısıtından dönecek.
2. Backend T7 kararını netleştirdiğinde (tek yön mü karşılıklı mı), engagement detay
   sayfasının `PENDING_EVALUATION` sonrası davranışını (örn. `EVALUATED` durumunu
   gösterme) buna göre güncelle.
3. `items[].skill_id` seçici istenirse eklenir (yukarıdaki kapsam kararı §1).

## Test durumu

- `lib/evaluation/schemas.test.ts` — Zod doğrulama kuralları.
- `lib/api/evaluation.test.ts` — mock submit akışı (başarı, 409, 422, 404, private_note
  gizliliği).
- `evaluation-form.test.tsx` — dinamik liste, doğrulama, başarılı gönderim payload'ı,
  hata gösterimi.
- `degerlendirme/page.test.tsx` — yükleniyor/uygun olmayan durum/zaten gönderilmiş/form.
- `calismalar/[id]/page.test.tsx`'e link görünürlüğü testleri eklendi.
- **Uçtan uca (gerçek backend ile) entegrasyon testi YAPILMADI.**
