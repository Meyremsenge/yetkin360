# Security Scan — admin-dogrulama-ve-skill-yonetimi-ekranlari

## Kapsam
`frontend/lib/api/admin.ts`, `frontend/app/admin/dogrulama-kuyrugu/page.tsx`,
`frontend/app/admin/skiller/page.tsx`, `frontend/messages/tr.json`,
`frontend/components/app-shell.tsx`

## Komut
```
scan.py . --files frontend/lib/api/admin.ts frontend/app/admin/dogrulama-kuyrugu/page.tsx
  frontend/app/admin/skiller/page.tsx frontend/messages/tr.json frontend/components/app-shell.tsx --json
```
Çıkış kodu: 1 (FAIL, ham)

## Gate Tablosu
| Gate | Sonuç | Gerekçe |
|---|---|---|
| Secrets (detect-secrets) | **FAIL (ham) → PASS (incelendikten sonra)** | 3 bulgu, hepsi `frontend/messages/tr.json` satır 41/66/67 — "Secret Keyword" tipi. İncelendi: bunlar `passwordLabel: "Şifre"`, `newPasswordLabel: "Yeni Şifre"`, `confirmPasswordLabel: "Yeni Şifre Tekrar"` UI etiket metinleri, gerçek bir sır/anahtar değil (detect-secrets'in "şifre"/"password" kelimesini anahtar kelimesi olarak yakalaması — bilinen yanlış pozitif deseni). **Ayrıca bu üç satır bu görevin diff'inde YOK** — `git diff -U0 -- frontend/messages/tr.json` kontrol edildi, bu görev sadece satır 18 (`errors.generic` metni) ve 214+ (yeni `adminVerificationQueue`/`adminSkills` anahtarları) ekliyor; 41/66/67 önceden var olan, bu görevden bağımsız satırlar. |
| Python SAST (bandit) | N/A | Değişen Python dosyası yok |
| Python bağımlılık (pip-audit) | N/A | Python bağımlılık manifestosu değişmedi |
| Node bağımlılık (npm audit) | N/A | `package.json` bu görevde değişmedi, yeni bağımlılık eklenmedi |
| JS/TS SAST | N/A (kapsam dışı) | `semgrep` bu ortamda kurulu değil — JS iş mantığı açıkları `red-team`'in kapsamında, ayrıca not düşüldü |

## Sonuç
**PASS** (koşullu) — tek bulgu, bu görevin diff'i dışında kalan, incelenmiş
bir yanlış pozitif (UI etiket metni). Bu görevin kendi eklediği kod/metin
(`admin.ts`, `page.tsx`'ler, yeni `tr.json` anahtarları) hiçbir secret/
bilinen-imza bulgusu üretmedi. Baseline'a yazmadım — bulgular bu görevin
kapsamı dışında olduğu için `--accept-secrets` bu görevin sorumluluğu değil,
gerekirse ayrı bir kullanıcı kararıyla ele alınmalı.

**Kapsam dürüstlüğü notu:** Bu tarama yalnız bilinen imza sınıflarını
(sızmış sır, Python CVE'si) kapsar. IDOR/yetkilendirme/iş mantığı açıkları
(AC-S1/AC-S2 gibi) bu skill'in kapsamında DEĞİL — onlar `red-team`'in işi.
