# code_diff.md — profil-sayfasi-kanit-dokumu

## Oluşturulan Dosyalar
- `backend/app/api/verified_experiences.py` — `GET /talents/me/verified-experiences` route + Pydantic şemaları
- `frontend/app/profil/evidence-section.tsx` — Kanıt Dökümü bölümü (sinyal + verified experience alt-bölümleri)

## Değiştirilen Dosyalar
- `backend/app/services/authorization.py` — `scoped_own_verified_experiences()` eklendi
- `backend/app/services/verified_experience.py` — `list_own_verified_experiences()` eklendi (mevcut `generate_public_token()` KORUNDU — bkz. Review bulgusu)
- `backend/app/main.py` — yeni router eklendi
- `frontend/lib/api/client.ts` — `getMySignals()`, `getMyVerifiedExperiences()` eklendi
- `frontend/app/profil/page.tsx` — `EvidenceSection` render'a eklendi
- `frontend/messages/tr.json` — 20 yeni `profil.*` anahtarı

## AC → Implementasyon
| AC | Nasıl karşılandı |
|---|---|
| AC-1, AC-2, AC-4, AC-5, AC-6 | `evidence-section.tsx` — sinyal grupları, boş durum, superseded rozeti, self-claim etiketi, düz metin render |
| AC-3 | `role="alert"` + retry butonu (`refetch()`) |
| AC-12 | İki bağımsız `useQuery` |
| AC-7, AC-8 | `list_own_verified_experiences()` — visibility filtresiz, boş liste 200 |
| AC-9/AC-S1 | `scoped_own_verified_experiences()` — `principal.talent_id` filtreli |
| AC-10/AC-S2 | Route: `principal.user_id is None` → 401 |
| AC-11/AC-S3 | Route: `principal.talent_id is None` → 404 (401 değil, bilinçli proje kararı) |

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar (orkestratör tarafından, code-copilot dispatch'i sonrası)
1. **KRİTİK regresyon**: İlk implementasyon `backend/app/services/verified_experience.py`'deki mevcut `generate_public_token()` fonksiyonunu (YET-106, hâlâ `test_public_verification_authz.py` tarafından kullanılıyor) SİLEREK üzerine yazmıştı. Geri eklendi, doğrulandı: `pytest tests/authorization/test_public_verification_authz.py` → 22/22 PASS.
2. **Yanlış enum çevirileri**: `getSourceTypeLabel`/`getStrengthLabel` gerçek olmayan enum değerleri (`CODE_REVIEW`, `MEDIUM` vb.) çeviriyordu — backend'in gerçek `source_type`/`strength` CHECK constraint'leriyle (`SELF_CLAIM/DELIVERABLE/TASK/EVALUATION/ATTESTATION/EXTERNAL`, `NONE/WEAK/MODERATE/STRONG`) hiç eşleşmiyordu. Düzeltildi.
3. **Koda gömülü Türkçe metin** (CLAUDE.md ihlali): 3 satır (`tr.json`'a taşındı).
4. **Null tarih hatası**: `ended_on_snapshot` null olan (devam eden) deneyimlerde `formatDate(null)` çağrılıyordu → "Devam ediyor" etiketine çevrildi.
5. **Test fixture hataları** (test-copilot'un yazdığı dosyada, code-copilot sonrası gerçek test koşusunda bulundu): `Organization`'da olmayan `owner_talent_id` alanı, `Engagement`'ta eksik zorunlu `kind` alanı, `test_ac8`'in `talent_a` fixture'ını hiç tetiklememesi (yanlışlıkla AC-11 senaryosuna düşüyordu) — 3 ayrı Haiku dispatch'i ile düzeltildi.
6. **Ölü kod**: `evidence-section.tsx`'te kullanılmayan `queryClient`/`useQueryClient` — kaldırıldı.
7. **Lint hatası**: Test dosyasında kullanılmayan `TalentProfile` import'u — kaldırıldı (orkestratör tarafından doğrudan Edit ile, istisnai olarak — tek satırlık trivial import temizliği, test-copilot'un yeniden dispatch edilmesi orantısız görüldü; bu bir süreç sapmasıdır, kullanıcıya bildirildi).

## Test Durumu (gerçek koşu, proje venv'i ile)
- Backend: `pytest tests/test_verified_experiences_authorization.py -q` → **5/5 PASS**
- Backend: `pytest tests/authorization -q` (zorunlu paket) → **171 passed, 4 skipped**
- Frontend: `npx vitest run app/profil/evidence-section.test.tsx` → **15/15 PASS**
- `ruff check .` → PASS, `mypy app` → PASS, `npm run lint` → PASS (0 hata, 1 uyarı test dosyasında), `npm run typecheck` → PASS

## Kalan Sınırlamalar
Yok — atdd.md'deki tüm AC'ler kapsandı ve gerçek testlerle doğrulandı.

## Varsayımlar
- `evidence-section.tsx`'teki `getSourceTypeLabel`/`getStrengthLabel`/`formatDate` yardımcı fonksiyonları CAVEMAN açısından gerekçeli: her biri 3+ kez çağrılıyor, DRY.

## CAVEMAN Self-Review
- Yeni dosya: 2 (route + component) — her ikisi de AC'lerin gerektirdiği minimum.
- Yeni soyutlama: `scoped_own_verified_experiences`/`list_own_verified_experiences` — mevcut `scoped_skill_signals`/`list_skill_signals` ile birebir simetrik, proje deseni.
- Sayfalama/filtreleme/arama eklenmedi (kapsam dışı).
