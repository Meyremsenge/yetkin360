# code_diff.md — public-profil-ve-dogrulama-sayfalari

## Oluşturulan Dosyalar
- `frontend/lib/api/public.ts` — `getPublicProfile()`, `getPublicVerification()`, credentials'sız `fetch()`
- `frontend/app/p/[slug]/page.tsx` — public profil sayfası, AppShell'siz
- `frontend/app/v/[token]/page.tsx` — doğrulama sayfası, AppShell'siz

## Değiştirilen Dosyalar
- `frontend/lib/auth/should-redirect.ts` — `isPublicRoute()`'a `/p/` ve `/v/` (eğik çizgili) eklendi
- `frontend/messages/tr.json` — `publicProfile`/`publicVerification` anahtarları
- `frontend/app/profil/page.test.tsx` — **ayrı bir görevin (YET-111, zaten push edilmiş) regresyonu düzeltildi** (bkz. Review bulguları)

## AC → Implementasyon
| AC | Nasıl karşılandı |
|---|---|
| AC-1, AC-2 | Sayfalar `getPublicProfile`/`getPublicVerification` çağırıp alanları render ediyor |
| AC-3, AC-4 | `ApiError.status===404` → "Kayıt bulunamadı" |
| AC-5 | `verified_experiences.length===0` → boş durum, 404 değil |
| AC-6 | `isPublicRoute()`'a `/p/`/`/v/` eklendi |
| AC-7/AC-S2 | `/p/` eğik-çizgili kontrol, `/profil` etkilenmiyor |
| AC-8 | `NetworkError` → genel mesaj |
| AC-9 | Düz metin render, `dangerouslySetInnerHTML` yok |
| AC-10 | `AppShell` kullanılmıyor |

## Review Sürecinde Bulunan ve Düzeltilen Sorunlar (orkestratör tarafından, code-copilot dispatch'i sonrası)
1. **CLAUDE.md ihlali**: İlk implementasyon her iki sayfada da çok sayıda Türkçe metni koda gömmüştü ("Kayıt bulunamadı", "Kurum", "Dönem" vb.) — `tr.json`'a eklenen anahtarlar bile kullanılmıyordu. Tümü `messages.*`'e taşındı.
2. **Nullable alan tip hatası** (tekrarlayan bir kalıp — önceki görevde de aynı sınıf hata bulunmuştu): `institution_name`, `started_on_snapshot`/`ended_on_snapshot`, `started_on`/`ended_on`, `attestor_organization` backend'de nullable ama TS tiplerinde non-null işaretlenmişti, null kontrolü yoktu. Tipler `| null` yapıldı, koşullu render eklendi.
3. **KRİTİK — ayrı bir görevin (YET-111) zaten push edilmiş regresyonu bulundu**: `app/profil/page.test.tsx`, `ProfilePage`'in artık render ettiği `EvidenceSection`'ı (YET-111'de eklendi) hiç mock'lamıyordu — gerçek `npx vitest run` (tüm suite) çalıştırılınca 2 test "No QueryClient set" hatasıyla FAIL etti. Bu, YET-111'in kendi verify adımında SADECE yeni test dosyaları çalıştırıldığı için (tüm suite değil) kaçırılmış bir regresyon. `evidence-section` için aynı mock deseni eklenerek düzeltildi.

## Test Durumu (gerçek koşu)
- `npx vitest run app/p app/v lib/auth/should-redirect.test.ts app/profil/page.test.tsx app/profil/evidence-section.test.tsx` → **105/105 PASS**
- `npm run lint` → 0 hata (3 uyarı, hepsi test dosyalarında)
- `npm run typecheck` → 0 hata
- **Not**: Tüm suite çalıştırıldığında (`npx vitest run`, 717 test) 3 dosyada (`lib/api/engagements.test.ts`, `lib/api/evaluation.test.ts`, `lib/api/evidence.test.ts`) 29 test `localStorage.clear is not a function` hatasıyla FAIL ediyor — bu dosyalar bu görevde HİÇ değiştirilmedi, izole çalıştırıldığında da aynı hatayı veriyor, pre-existing bir ortam sorunu (muhtemelen jsdom/vitest sürüm uyumsuzluğu). Bu görevin kapsamı dışı, ayrıca not düşüldü (verify_report.md'de detaylı).

## Kalan Sınırlamalar
Yok — atdd.md'deki tüm AC'ler kapsandı.

## CAVEMAN Self-Review
- Yeni dosya: 3 (api client + 2 sayfa) — minimum gerekli.
- `fetchWithTimeout`/`handleResponse` yardımcı fonksiyonları `public.ts`'te — AC-8 (network/timeout hatası) için gerekli, gerekçeli.
- AppShell kullanılmadı (kasıtlı, AC-10).
