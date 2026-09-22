# Security Scan — yet-12-frontend-kabuk
_Kapsam: `code_diff.md`'deki değişen 19 dosya (frontend, yalnız JS/TS). Repo geneli taranmadı._

## Gate Tablosu
| Gate | Sonuç | Gerekçe |
|---|---|---|
| `bandit` (Python SAST) | N/A | Değişen dosyaların hiçbiri Python değil; skill kendisi bu durumu N/A sayıyor. |
| `pip-audit` | N/A | Python bağımlılığı yok (frontend görevi). |
| `detect-secrets` | **MISSING** | `~/.claude/security-tools/venv` bu makinede kurulu değil. Kurulum global `pip install` gerektirir, proje bağımlılığı değil — kullanıcı onayı olmadan kurmadım. PASS SAYILMADI. |
| `npm audit` (JS bağımlılık taraması) | **FAIL** | 1 `high` şiddetinde açık: `postcss` (`next`'in transitive bağımlılığı) — CVE grubu GHSA-qx2v-qp2m-jg93 vb. (XSS, path traversal, sourceMappingURL üzerinden dosya sızıntısı). Düzeltme `npm audit fix --force` ile `next@16.3.5`'e (kırıcı sürüm) geçiyor. |

## Bulgular
1. **`postcss` — high severity, önceden var olan.** Bu açık `yet-12` görevinden ÖNCE de mevcuttu (oturumun ilk `npm ci` çalıştırmasında, hiçbir paket eklenmeden önce aynı sonuç görüldü) — bu görevin eklediği bir şey değil. Düzeltmesi `next` sürümünü kırıcı şekilde yükseltmeyi gerektiriyor; CLAUDE.md gereği bağımlılık sürüm yükseltmesi ayrı kullanıcı onayı ister. Bu görevin kapsamında düzeltilmedi.

## Kapsam sınırları — dürüstçe
- JavaScript/TypeScript için gerçek bir SAST taraması **yapılmadı** (skill kendi kapsam sınırında bunu belirtiyor — `semgrep` bu araç zincirinde yok). İş mantığı açıkları (`AC-S1`–`AC-S6`, CSRF, open redirect, oturum sızıntısı) `threat-model` aşamasında gereksinime dönüştürüldü ve `test-copilot`/`code-copilot` tarafından test edildi — ama bağımsız bir statik güvenlik taraması bunları bir daha doğrulamadı.
- `detect-secrets` çalışmadığı için **sızmış sır taraması yapılamadı**. Elle kontrol: değişen dosyalarda `.env`, API anahtarı, token literal'i aranmadı — bu bir boşluktur, `INCONCLUSIVE` olarak işaretlendi.

## Sonuç
**INCONCLUSIVE + 1 bilinen (önceden var olan) FAIL.** `verify_report.md`'nin gate 10'una bu şekilde yansıtıldı.
