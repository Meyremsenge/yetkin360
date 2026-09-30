# Authz Test Matrisi — guv-02-davet-yaniti-duzeltmesi
_Reference: atdd.md AC-S1 (AC-7), AC-S5 (AC-8)_

Bu dosya testleri YAZMAZ — `test-copilot`'a `extra_instructions` olarak verilecek saldırgan-perspektifi matrisidir. Canlı sonda bu oturumda çalıştırılmadı (kullanıcı onayı istenmedi, ayrıca Supabase değil — bu proje kendi PostgreSQL/FastAPI'si, bu skill'in "canlı sonda" bölümü öncelikle Supabase/RLS için tasarlanmış; burada karşılığı zaten `pytest tests/authorization -q`'nun gerçek DB'ye karşı çalışmasıdır, `verify` adımında yapılacak).

## Matris — `POST /organizations/{id}/members`

| # | Aktör | Girdi | Beklenen | AC |
|---|---|---|---|---|
| 1 | Org X'in ADMIN'i (sahibi) | bilinen e-posta, geçerli rol | `202 {"status":"queued"}`, üyelik DB'de oluşur | AC-1 |
| 2 | **Org Y'nin ADMIN'i** (başka kiracı) | Org X'e davet göndermeye çalışır | `404` — Org X hakkında hiçbir alan gövdede olmamalı | AC-7 (AC-S1) |
| 3 | Org X'in MEMBER'ı (ADMIN değil) | Org X'e davet göndermeye çalışır | `404` (mevcut davranış — regresyon) | AC-7 (AC-S1) |
| 4 | Kimliksiz | herhangi bir davet | `401` | AC-7 (AC-S1, mevcut auth dependency zaten sağlıyor) |
| 5 | Org X ADMIN'i | bilinmeyen e-posta | `202 {"status":"queued"}` — AYNI şekil, üyelik OLUŞMAZ (DB'de doğrula: yeni satır yok) | AC-2 |
| 6 | Org X ADMIN'i | geçersiz rol (`"SUPERADMIN"` gibi) | `422 ApiError{code:"INVALID_ROLE"}`, DB'ye dokunulmaz | AC-3 |
| 7 | Org X ADMIN'i | zaten üye olan kullanıcı | `202 {"status":"queued"}` — rol DB'de DEĞİŞMEMİŞ olmalı (yazma testinde son durumu doğrula) | AC-4 |
| 8 | İstekte `role: "ADMIN"` ile rol yükseltme denemesi (davet edilen kullanıcı kendi payload'ında değil, davet EDEN zaten ADMIN olmalı — bu uç zaten ADMIN yetkisi istiyor) | mevcut ADMIN kontrolü | Yalnız gerçek ADMIN başarılı olur, taklit edilemez | AC-7 |

## Matris — `POST /institutions/{id}/members`

| # | Aktör | Girdi | Beklenen | AC |
|---|---|---|---|---|
| 1 | Kurum X'in ADMIN'i (sahibi) | bilinen e-posta, geçerli rol | `202 {"status":"queued"}`, üyelik DB'de oluşur, audit event yazılır | AC-1, AC-6 |
| 2 | **Kurum Y'nin ADMIN'i** (başka kiracı) | Kurum X'e davet göndermeye çalışır | `404` | AC-8 (AC-S5) |
| 3 | **Kurum X'in COORDINATOR'ı** (ADMIN değil) | Kurum X'e davet göndermeye çalışır | `404` (mevcut davranış — regresyon, threat-model'in özellikle vurguladığı satır) | AC-8 (AC-S5) |
| 4 | Kimliksiz | herhangi bir davet | `401` | AC-8 |
| 5 | Kurum X ADMIN'i | bilinmeyen e-posta | `202 {"status":"queued"}` — AYNI şekil, üyelik OLUŞMAZ, audit event yazılır (e-posta yazılmadan) | AC-2, AC-6 |
| 6 | Kurum X ADMIN'i | geçersiz rol | `422 ApiError{code:"INVALID_ROLE"}`, DB CHECK'e hiç düşmez | AC-3 |
| 7 | Kurum X ADMIN'i | zaten üye olan kullanıcı (kendisi dahil — **son ADMIN senaryosu**) | `202 {"status":"queued"}` — rol DB'de DEĞİŞMEMİŞ, tek ADMIN korunur | AC-4, AC-5 |
| 8 | Kurum X'te tek ADMIN, kendini COORDINATOR rolüyle tekrar davet ediyor | aynı senaryo, açıkça "son admin" testi | Rol ADMIN olarak kalır — DB'den tekrar okuyarak doğrula | AC-5 |

## İki kural — test-copilot'a hatırlatma
- **Boş liste/başarı geçmek değildir**: satır 2/3 (her iki tablo) `404` dönmeli, `200 + []` gibi sessiz bir filtreleme DEĞİL.
- **Yazma testinde son durumu doğrula**: satır 7/8 (her iki tablo) yalnız durum kodunu değil, DB'den üyeliği tekrar okuyup rolün gerçekten değişmediğini doğrulamalı — bu tam olarak AC-4/AC-5'in test edilmesi gereken kısmı, sadece HTTP yanıtına bakmak yeterli değil.
- **Mock yasak**: bu testler gerçek test DB'sine karşı, `tests/authorization/` konvansiyonuyla (gerçek PostgreSQL, testcontainers) yazılmalı.

## Canlı sonda
N/A bu oturumda — kullanıcı onayı istenmedi, ayrıca bu proje Supabase/RLS kullanmıyor (kendi PostgreSQL + FastAPI yetkilendirme çekirdeği). Matrisin gerçek doğrulaması `verify` adımında `pytest tests/authorization -q` (tam paket, gerçek DB) ile yapılacak.

## Kapsanmayan
- Rol yükseltme denemesi (davet EDİLEN kişinin kendi isteğiyle role=ADMIN talep etmesi) bu uçta zaten mümkün değil — rol davet EDEN'in payload'ında, davet edilenin değil. Bu satır matrise "kapsanmıyor, çünkü uç zaten bu saldırı yüzeyini açmıyor" notuyla eklendi (satır 8, org tablosu).
