# Verify Report — koordinator-dashboard-frontend
_Reference: atdd.md, plan.md, test_diff.md, code_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` ile `frontend/lib/api/institutions.ts`, `frontend/app/kurum/[id]/panel/page.tsx` (+ testleri), `frontend/messages/tr.json` diff'i doğrulandı |
| 2 | Build/derleme | PASS | `npm run build` (CI'nin kendi komutu) → "Compiled successfully", `/kurum/[id]/panel` route'u üretim çıktısında listelendi (1.57 kB, ƒ dynamic) |
| 3 | Supabase şema/canlı doğrulama | N/A | Bu görev Supabase kullanmıyor (proje PostgreSQL + FastAPI/SQLAlchemy kullanıyor), migration/şema değişikliği yok |
| 4 | Lint | PASS (4 pre-existing uyarı) | `npm run lint` (CI komutu) → 0 hata, 4 uyarı — biri bizim `page.test.tsx`'te (`'scripts' is assigned a value but never used`, satır 379), test-copilot'un yazdığı test dosyasında kullanılmayan bir değişken; diğer 3 uyarı önceden var olan başka test dosyalarında. Hata değil, bloklayıcı değil. |
| 5 | Type check | PASS | `npm run typecheck` (CI komutu, `tsc --noEmit`) → sıfır hata |
| 6 | Unit testler | PASS | `npx vitest run lib/api/institutions.test.ts "app/kurum/[id]/panel/page.test.tsx"` → **2 dosya, 21/21 test PASS**. Her AC (1,2,3,4,5,6/S1,7) + Davranış Sözleşmesi satırları test kapsamında (bkz. test_diff.md). |
| 7 | E2E testler | KISMEN — smoke test | Proje çapında Playwright/Cypress e2e suite yok (CI'de yok). Playwright değil ama gerçek tarayıcıda (Claude Browser) `/kurum/test-inst-1/panel`'e kimliksiz erişim denendi → doğru şekilde `/giris?next=%2Fkurum%2F...` yönlendirmesi gözlendi (auth-guard çalışıyor, veri sızıntısı yok). **Kimliği doğrulanmış tam happy-path render doğrulanamadı** — PLAN 3.11 (seed verisi: kurum/koordinatör hesabı) henüz tamamlanmadığı için gerçek bir COORDINATOR hesabı bu ortamda yok. Bu bir N/A değil, açık bir sınırlama olarak kaydedildi. |
| 8 | Lighthouse (performans) | N/A | Lighthouse MCP bu oturumda kurulu değil; kimliği doğrulanmış bir sayfa olduğu için zaten anlamlı bir ölçüm gerçek oturum gerektirir (bkz. gate 7) |
| 9 | Erişilebilirlik | KISMEN (statik inceleme) | `frontend-pipeline` Audit adımında (plan öncesi) `AppShell`/`ErrorBanner`/benzer sayfa kalıbı statik olarak incelendi: `role="alert"`, native `<button>` (focus-ring korunuyor), semantik `<section>`/`<h2>` kullanımı doğrulandı — kod bu kalıbı birebir taşıyor. Gerçek render üzerinde otomatik bir accessibility taraması (Lighthouse) çalıştırılamadı (bkz. gate 8). |
| 10 | Güvenlik taraması | PASS (pre-existing false-positive hariç) | `security-scan` çalıştırıldı, scope: değişen 3 dosya. `tr.json`'da 3 "Secret Keyword" bulgusu çıktı ama hepsi satır 41/66/67 — bizim eklediğimiz satırlar DEĞİL (bizim ekimiz satır 205-213), `git stash` ile doğrulandı: bu satırlar önceden var olan `"passwordLabel": "Şifre"` gibi UI etiketleri, gerçek sır değil (detect-secrets'ın "password" kelimesi heuristic'i). Bizim eklediğimiz kodda (institutions.ts, page.tsx, tr.json'daki yeni `kurumPanel` anahtarı) sıfır bulgu. |
| 11 | AI code review | PENDING (red-team) | Ayrı adımda yapılacak |
| 12 | Görsel regresyon | KISMEN | `vision-test`/Lighthouse ile otomatik screenshot-diff çalıştırılamadı (gerekçe: gate 7/8 ile aynı — auth arkasında, seed verisi yok). Statik kod incelemesi + gerçek tarayıcıda auth-guard smoke testi yapıldı. Tam görsel doğrulama için PLAN 3.11 tamamlandıktan sonra bu görev için ayrı bir görsel doğrulama turu ÖNERİLİR. |
| 13 | DAST (ZAP) | N/A | `threat-model` adımı AC-S1 (tenant cache-izolasyonu, istemci tarafı) ve AC-S2 (jenerik mesaj) ürettі ama ikisi de sunucu-taraflı değil istemci-taraflı davranışlar — ZAP'ın kapsadığı canlı HTTP yüzeyi bu görevde genişlemedi (aynı backend ucu zaten kullanılıyor, `koordinator-dashboard-ucu` görevinde DAST'a tabi tutulmuş olabilir). |
| 14 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor |

## Refactor Aday Kontrolü
Aday yoksa/varsa kontrolü yapıldı: `institutions.ts` (33 satır, tek fonksiyon, sıfır dallanma) ve `page.tsx` (110 satır, tekrarlanan iki liste bloğu var ama görsel olarak farklı empty-state/alan adları taşıyor — bir yardımcı component'e çıkarmak bu aşamada spekülatif soyutlama olurdu, CAVEMAN ilkesine aykırı) incelendi. Sihirli sayı yok, derin nesting yok (`useQuery` + üç koşullu render, JSX içinde en fazla 3 seviye), uzun parametre listesi yok, ölü kod yok.
**Refactor adayı yok** (diff zaten minimal/CAVEMAN'a uygun).

## AC -> Test Mapping
1. AC-1 (happy path) → `AC-1: happy path...` (institutions.test.ts + page.test.tsx) → PASS
2. AC-2 (boş liste) → `AC-2: empty list/empty state...` → PASS
3. AC-3 (404 jenerik) → `AC-3: 404...` + `Davranış Sözleşmesi: 404 gösterilir (403 değil)` → PASS
4. AC-4 (401) → `AC-4: 401...` → PASS
5. AC-5 (network/500) → `AC-5: Network error/Server error/ErrorBanner...` → PASS
6. AC-6/AC-S1 (tenant cache-izolasyonu) → `AC-6/AC-S1: Tenant isolation/cache key...` → PASS
7. AC-7 (XSS/escape) → `AC-7: XSS riski/XSS prevention...` → PASS

## Red-team Sonrası Düzeltme (2. tur)
Red-team `approve-with-changes` verdict'i verdi, 2 medium bulgu (`reliability`: `SessionExpiredError` sayfa içinde ele alınmıyordu; `test-gap`: AC-4 testi bu davranışı doğrulamıyordu) kullanıcı onayıyla düzeltildi:
- `page.test.tsx` AC-4 testi güçlendirildi (test-copilot Haiku dispatch) — artık `messages.session.expired` mesajının göründüğünü VE jenerik mesajın görünmediğini tam eşleşmeyle doğruluyor. Önce KIRMIZI olduğu doğrulandı (10/11).
- `page.tsx`'e `error instanceof SessionExpiredError` dalı eklendi (code-copilot Haiku dispatch, tek satırlık minimal değişiklik, router yönlendirmesi eklenmedi — AppShell'in kendi session akışına bırakıldı).
- Yeniden çalıştırma: `npx vitest run lib/api/institutions.test.ts "app/kurum/[id]/panel/page.test.tsx"` → **21/21 PASS**. `npm run lint` → 0 hata (aynı 4 pre-existing uyarı). `npm run typecheck` → 0 hata.
- Düşük öncelikli 4 bulgu (stale-while-revalidate göstergesi, tarih parse, liste tekrarı, elle yazılmış tipler) kullanıcı kararıyla bu turda kapsam dışı bırakıldı — `red_team.json`'da kayıtlı, gelecekte `postmortem` tarafından izlenebilir.

## Coverage / Quality Notes
- Tüm AC'ler test kapsamında, hiçbir satır testsiz bırakılmadı.
- Bir küçük lint uyarısı (kullanılmayan `scripts` değişkeni, `page.test.tsx:379`) — bloklayıcı değil, `red-team`/temizlik adımında gerekirse düzeltilebilir, ayrı bir `refactor` gerektirmez (test dosyasında, üretim kodunda değil).
- **Bilinen sınırlama:** Bu görev gerçek bir COORDINATOR/INST_ADMIN oturumuyla uçtan uca (gerçek backend + gerçek veri) test edilemedi — PLAN 3.11 (seed verisi) bağımlılığı. Kullanıcıya bildirilmeli.
