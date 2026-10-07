# Verify Report — tasarim-sistemi-temel-bilesenler
_Reference: atdd.md, code_diff.md, test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` ile 4 dosya (1 değişen + 3 yeni) doğrulandı; `Read` ile içerik satır satır incelendi. |
| 2 | Build/derleme | PASS | `npm run build` (Next.js 16.3.8) — 20/20 sayfa üretildi, hata yok. |
| 3 | Supabase şema/canlı doğrulama | N/A | Saf frontend UI bileşen kodu, DB'ye dokunmuyor. |
| 4 | Lint | PASS | `npm run lint` — 0 hata, 6 önceden var olan ilgisiz uyarı. |
| 5 | Type check | PASS | `npm run typecheck` (`tsc --noEmit`) — hatasız. |
| 6 | Unit testler | PASS | `npx vitest run components/ui/{button,card,badge,alert}.test.tsx` → 95/95 PASS. Tüm suite: `npm run test` → 66 dosya, **1134/1134 PASS** (1039 önceki + 95 yeni, 0 regresyon — AC-9 gerçek koşuyla kanıtlandı). |
| 7 | E2E testler | N/A | atdd.md'nin bilinçli kararı: hiçbir sayfa bu bileşenleri henüz kullanmıyor (migrasyon ayrı görev), e2e'ye konu yok. |
| 8 | Lighthouse (performans) | N/A | Kapsam dışı, performans hedefi atdd.md'de null. |
| 9 | Erişilebilirlik | N/A | Gate 8 ile aynı koşul. |
| 10 | Güvenlik taraması | PASS | `security-scan` — secrets PASS, verdict PASS (Python/Node bağımlılık taraması N/A, saf TS/TSX değişikliği). |
| 11 | AI code review | PENDING (red-team) | Sonraki adımda yapılacak. |
| 12 | Görsel regresyon | N/A | atdd.md'nin bilinçli kararı — hiçbir sayfa bu bileşenleri kullanmadığı için vision-test'e konu render yok. Tek görsel garanti (button.tsx'in mevcut kullanıcıları) gate 6'daki tam suite koşusuyla (1134/1134) kanıtlandı. |
| 13 | DAST (ZAP) | N/A | `threat_model: not-applicable` — tetikleyici yok. |
| 14 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor. |

## AC -> Test Mapping
| AC | Test | Sonuç |
|---|---|---|
| AC-1 (happy path, geriye dönük uyumluluk) | button.test.tsx "AC-1" (6 test) | PASS |
| AC-2 (destructive) | button.test.tsx "AC-2" (4 test) | PASS |
| AC-3 (secondary/ghost) | button.test.tsx "AC-3" (5 test) | PASS |
| AC-4 (size sm/md/lg) | button.test.tsx "AC-4" (9 test) | PASS |
| AC-5 (className override, KRİTİK) | button.test.tsx "AC-5" (4 test, 1'i düzeltildi) | PASS |
| AC-6 (Alert) | alert.test.tsx (27 test) | PASS |
| AC-7 (Badge) | badge.test.tsx (21 test) | PASS |
| AC-8 (Card) | card.test.tsx (13 test) | PASS |
| AC-9 (regresyon) | button.test.tsx "AC-9" (6 test) + tam suite (1134/1134) | PASS |

## Coverage / Quality Notes
- Her AC'nin birden fazla testi var, test piramidi atdd.md'nin öngördüğü (unit 85/integration 15/e2e 0) ile tam uyumlu.
- **Code-copilot aşamasında 2 gerçek sorun bulunup düzeltildi** (bkz. `code_diff.md` "Review Sürecinde Bulunan ve Düzeltilen Sorunlar"): (1) implementasyonda icat edilmiş, atdd.md'de olmayan bir `hasBackgroundOverride` kısayolu; (2) testte substring-çakışması nedeniyle yanlışlıkla kırmızı bir assert. İkisi de alt-ajanın "tüm testler PASS" raporuna güvenilmeyip gerçek `Read`/test koşusuyla yakalandı.
- cva bağımlılığı eklenmedi, mevcut `cn()` (clsx+tailwind-merge) kullanıldı — atdd.md'nin Assumptions bölümündeki kullanıcı onaylı karar uygulandı.

## Refactor Aday Kontrolü
Refactor adayı yok — 4 dosya da minimal, tek sorumluluklu, tekrar/sihirli sayı/derin nesting/uzun parametre listesi yok (variant/size map'leri `Record<string,string>` ile açık ve okunabilir).

## Red-Team Sonrası Ek Düzeltme
Red-team, `alert.tsx`'in `.claude/rules/frontend.md` kuralını ("Hata mesajları aria-live ile duyurulur") karşılamadığını buldu (medium, erişilebilirlik). `role="alert"` + koşullu `aria-live` (`error` → `assertive`, diğerleri → `polite`) eklendi. `alert.test.tsx` (27/27) ve typecheck sonrası tekrar PASS.
