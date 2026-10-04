---
task_slug: yet-212-hata-yanit-bicimi
jira_id: YET-212
saga_task_id: null
priority: medium
threat_model: not-applicable
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 80
  e2e: 0
affected_modules:
  - backend/app/main.py
  - backend/app/core/errors.py
  - backend/app/api/organizations.py (str detail 429 vb. kodlar)
  - docs/API.md (§1.4), docs/ENV.md
---

# ATDD — yet-212-hata-yanit-bicimi

## Jira Kaynağı
YET-212 — OPS-04: Hata yanıt biçimi tutarsız (Hata, Medium). Açıklama (birebir özet): tanımsız yol `{"detail":"Not Found"}` dönüyor (docs/API.md §1.4 `{code,message,request_id}` sözleşmesine uymuyor); `HTTPException(detail=...)` kullanan uçlar `code:"HTTP_ERROR"` dönüyor; engagement uçlarında request_id None; yakalanmayan istisnalar düz 500; `/docs`/`/openapi.json` üretimde açık, debug=True varsayılan. Detay: HATA.md §7 OPS-04.

## Persona
Frontend geliştiricisi / destek ekibi: hata koduna göre dallanır, kullanıcı destek talebinde request_id verir.

## Hedef (Neden)
Her hata yanıtı tek biçimde olsun, her biri log ile eşleşebilsin, iç ayrıntı sızmasın.

## Kanıt (sonda, test DB yetkin360_test, rate_limit_enabled=False; 429 koşusunda True)
- 404 bilinmeyen yol, 405 yanlış yöntem: `{"detail": ...}` (AÇIK)
- str-detail HTTPException: `code: HTTP_ERROR`, `message` = ham (çoğu İngilizce) detail, request_id null (AÇIK)
- dict-detail HTTPException (engagement 80 yer, me, talent_skills): request_id null (AÇIK)
- 422: request_id null, `fields` yok (API.md'ye aykırı) (AÇIK)
- işlenmeyen istisna: `text/plain "Internal Server Error"`, id yok (AÇIK)
- ApiError: her hatada taze UUID, loga yazılmıyor (korelasyon yok) (AÇIK)
- 401/403(CSRF)/429(login) ApiError ile uyumlu: KAPALI (yalnız id log'a bağlı değil)
- /docs, /openapi.json açık; `settings.debug` kodda hiç kullanılmıyor (ölü bayrak)

## Acceptance Criteria
1. [Critical] Given herhangi bir hata (404 yol, 405, HTTPException, ApiError, 422, 500), When yanıt alınır, Then gövde JSON `{code, message, request_id}` ve `request_id` dolu.
2. [Critical] Given istek, When hata olur, Then gövdedeki request_id `X-Request-ID` yanıt başlığıyla aynı ve sunucu logunda aynı id ile kayıt var.
3. [Critical] Given işlenmeyen istisna, When 500, Then JSON `INTERNAL_ERROR` + Türkçe sabit mesaj; istisna metni/yığın/SQL yanıtta yok; log'da yığın+request_id var.
4. [High] Given str detail HTTPException, When yanıtlanır, Then detail SCREAMING_SNAKE ise `code`=detail, değilse duruma göre genel kod (NOT_FOUND, …); `message` Türkçe genel mesaj, `HTTP_ERROR` kalmaz.
5. [High] Given 422, When yanıtlanır, Then `fields` {alan: mesaj} içerir (API.md §1.4).
6. [High] Given tanımsız yol/yöntem, When istek, Then `NOT_FOUND` / `METHOD_NOT_ALLOWED` (405 `Allow` başlığı korunur).
7. [High] Given yetkisiz kaynak erişimi, Then 404 davranışı DEĞİŞMEZ; CSRF 403, kimlik 401, hız 429 (+Retry-After) davranışı DEĞİŞMEZ.
8. [Medium] Given ENVIRONMENT=production, When /docs, /redoc, /openapi.json, Then 404 (JSON hata gövdesiyle); development'ta açık.
9. [Medium] Frontend `parseApiError` değişmeden çalışır (anahtarlar aynı).

## Davranış Sözleşmesi
| # | Durum | Dönen | Yan etki | Kullanıcı görür | AC |
|---|---|---|---|---|---|
| 1 | Bilinmeyen yol | 404 NOT_FOUND | log | "Kaynak bulunamadı." | 1,6 |
| 2 | Yanlış yöntem | 405 METHOD_NOT_ALLOWED + Allow | log | genel mesaj | 6 |
| 3 | Girdi geçersiz | 422 VALIDATION_ERROR + fields | — | alan altı hata | 5 |
| 4 | str-detail HTTPException | durum korunur, code=detail veya genel | — | Türkçe mesaj | 4 |
| 5 | Yetkisiz kaynak | 404 (değişmez) | — | — | 7 |
| 6 | CSRF / kimlik / hız | 403 / 401 / 429 (değişmez) | — | — | 7 |
| 7 | Dış bağımlılık / beklenmeyen | 500 INTERNAL_ERROR | log+yığın | "Beklenmeyen bir hata oluştu." + id | 3 |
| 8 | Kısmi başarı | N/A: tek istek tek yanıt; hata öncesi commit olmaz (get_session rollback) | — | — | — |
| 9 | Hata yok ama sonuç yok | N/A (hata yolu değil) | — | — | — |
Boş sonuç ↔ hata: değişmez (200+[] vs 404 mevcut davranış).

## Kapsam Dışı
Çağıranlarda 124 HTTPException satırının tek tek yeniden yazılması; yeni hata kodu kataloğu; /health değişikliği; debug bayrağının ENV.md dışı anlamı (kodda kullanılmıyor); config.py (YET-207 dalı alanı).

## Etkilenen
main.py, core/errors.py, yeni tests/test_error_contract.py, docs/API.md §1.4, docs/ENV.md.

## Rollback
Handler'lar tek dosyada; geri alma = commit revert. Migration/bağımlılık yok.

## Risks
- Mevcut testler `HTTP_ERROR`/`detail` metnine bağlı olabilir (grep ile doğrulanacak).
- Dev ortamı /docs'a bağlı: yalnız production'da kapanır.
- Middleware ile istisna sırası (500 CORS başlığı): ServerErrorMiddleware CORS dışında kalır.

## Assumptions (kullanıcı onayı bekliyor)
- Kod eşlemesi, 422 mesajı ve docs kapatma kararları aşağıdaki plan onayında netleşir.

## Unknowns
- Frontend UI'nın 422 `message`'ını doğrudan gösterip göstermediği.
