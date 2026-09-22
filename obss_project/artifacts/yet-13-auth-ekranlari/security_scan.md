# Security Scan — yet-13-auth-ekranlari

## Kapsam
`code_diff.md`'deki değişen/yeni frontend dosyaları (page/form/lib/messages/package.json). Test dosyaları kapsam dışı.

## Gate Sonuçları
| Araç | Sonuç | Gerekçe |
|---|---|---|
| `detect-secrets` | **MISSING** | `~/.claude/security-tools/venv` bu makinede kurulu değil (scan.py bulunamadı). PASS SAYILMADI. |
| `bandit` | N/A | Python kodu değişmedi (bu görev tamamen frontend/TypeScript). |
| `pip-audit` | N/A | Python bağımlılığı değişmedi. |
| `npm audit --audit-level=high` | **FAIL (pre-existing, bu görevle ilgisiz)** | `next`'in transitive `postcss` bağımlılığında 1 high (XSS/path traversal) + 1 moderate CVE var. `git diff frontend/package.json` `next`/`react` satırlarını DEĞİŞTİRMEDİ — bu açık YET-13'ten önce de vardı, bu görevin eklediği bağımlılıklardan (react-hook-form, zod, @hookform/resolvers, radix-label, clsx, tailwind-merge, testing-library paketleri) kaynaklanmıyor. Ayrı bir bağımlılık yükseltme kararı gerektirir (`npm audit fix --force` → Next 16'ya majör geçiş, CLAUDE.md "sürüm yükseltme" onay kuralı kapsamında, bu görevin dışında). |
| Manuel sır taraması (grep: API key/secret/token/password literal, AWS key deseni, PEM header) | PASS | Değişen dosyaların diff'inde eşleşme yok. |

## Sonuç
Bu görevin **kendi** eklediği kodda bilinen bir imza-tabanlı açık bulunamadı (detect-secrets aracı eksik olduğu için bu iddia sınırlı — "bilinen imzalarda sızıntı yok" değil, "araçla taranamadı, manuel kontrol temiz" diye okunmalı). `npm audit`'teki tek bulgu bu görevden önce var olan, `next` sürümüyle ilgili bir CVE — ayrı ele alınmalı.

**Tavsiye:** `detect-secrets` aracının bu makineye kurulması (`pip install detect-secrets` içinde izole bir venv'e) ayrı bir altyapı işi olarak `postmortem`'e not düşülsün.
