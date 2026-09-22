# Security Scan — yet-14-talent-profil-yetkinlik

## Kapsam
`code_diff.md`'deki değişen/yeni frontend dosyaları. Test dosyaları kapsam dışı.

## Gate Sonuçları
| Araç | Sonuç | Gerekçe |
|---|---|---|
| `detect-secrets` | **MISSING** | `~/.claude/security-tools/venv` bu makinede kurulu değil (YET-13'te de aynı durum tespit edildi). PASS SAYILMADI. |
| `bandit` | N/A | Python kodu değişmedi. |
| `pip-audit` | N/A | Python bağımlılığı değişmedi. |
| `npm audit --audit-level=high` | **FAIL (pre-existing, bu görevle ilgisiz)** | `next`'in transitive `postcss` bağımlılığında 1 high CVE — YET-13'te de tespit edilmişti, bu görev hiçbir yeni bağımlılık eklemedi (`package.json` bu görevde değişmedi), açık bu görevden önce de vardı. |
| Manuel sır taraması (grep: API key/secret/token/password literal, AWS key deseni, PEM header) | PASS | Değişen dosyaların diff'inde eşleşme yok. |

## Sonuç
Bu görevin **kendi** eklediği kodda bilinen bir imza-tabanlı açık bulunamadı. `npm audit`'teki tek bulgu YET-13'te de raporlanan pre-existing `next`/`postcss` CVE'si — bu görev `package.json`'a dokunmadı (0 yeni bağımlılık), dolayısıyla bu görevin sorumluluğunda değil.
