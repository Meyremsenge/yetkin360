# HANDOFF — YET-212 (OPS-04 hata yanıt biçimi): kod bitti, kalan yalnız Jira onayı ve sonraki iş

(Önceki içerik YET-69 devriydi, eskidi; git geçmişinde duruyor.)

## Yeni oturuma başlarken
1. `CLAUDE.md` ve hafıza `jira-yet-gorev-kuyrugu.md` (YET-212 maddesi `[x]`, açık takipler orada) oku. Başka şeye başlama.
2. Branch: `fix/yet-212-hata-yanit-bicimi` (origin/main'den, commit `29c4090`, push edildi, PR yok). Çalışma ağacı temiz; tek takipsiz öğe bilinen `obss_project/artifacts/yet-241-237-alan-adi-kisitlari/` (dokunma).
3. Docker Postgres/MinIO ayakta olmalı (`docker compose up -d`). Python: `backend/.venv/Scripts/python.exe`.

## Hedef
Jira YET-212: tüm hata yanıtları docs/API.md §1.4 `{code, message, request_id}` biçiminde olsun, request_id dolu ve loglu, 500 JSON, `/docs` üretimde kapalı.

## Yapılanlar (bitti, doğrulandı)
- `backend/app/core/errors.py`: `RequestIdMiddleware` (istek başı UUIDv7, istemci başlığı yok sayılır, `X-Request-ID`), Starlette HTTPException / RequestValidationError / Exception handler'ları, `ApiError` request_id'yi handler'dan alır.
- `backend/app/main.py`: `create_app(environment)`; production'da `/docs`, `/redoc`, `/openapi.json` kapalı; CORS `expose_headers`. Dosya CRLF, korundu.
- `backend/tests/test_error_contract.py`: 16 test. `docs/API.md` §1.4 güncel. `obss_project/artifacts/yet-212-hata-yanit-bicimi/atdd.md`.
- Kullanıcı kararları (onaylı): gövde anahtarları aynı; 422 `message` = "Girdi doğrulanamadı." + `fields`; docs production'da kapalı.
- Sonuç: backend 1291 geçti/5 skip, authz 686/4, ruff + mypy temiz, security-scan PASS, 11 mutasyon hepsi kırmızı. Yetkisiz=404, CSRF 403, 401, 429 değişmedi. Sondalar test DB'de koşuldu (`rate_limit_enabled=False`, 429 koşusunda True), dev DB'ye satır bırakılmadı.

## Ne işe yaradı
- Sondayı geçici pytest olarak yazıp koşturup silmek; yeni test dosyasını önce yazmak; mutasyon betiğini sıralı koşturmak (bayt düzeyinde replace, CRLF/LF korunur).
- `detect-secrets` `_SECRET` adlı değişkeni işaretledi → `_LEAK_MARKER` olarak değiştirildi.

## Ne işe yaramadı
- Starlette `ServerErrorMiddleware` kendi yanıtını gönderir: `X-Request-ID` başlığını 500 handler'ında elle koymak gerekti.
- Test'te kaynak satırdaki sabit, traceback frame'inde görünür → sızıntı testi için çalışma zamanı değeri kullan.
- `Monitor` aracı şemasız çağrılınca hata verdi; arka plan görevinde `sleep` bloklandı, bildirimi beklemek yeterli.

## Sıradaki adımlar
1. **Jira (onay bekliyor, yapılmadı):** YET-212'ye yorum + Tamamlandı (geçiş id 31) ÖNER; kullanıcı onaylarsa yap. Yorumda: kapsam (yukarıdaki), 11 mutasyon, açık takipler.
2. **Açık takipler (Jira'da görevi yok, hafızada ayrıntılı):** uvicorn 500'de istisna metniyle yığın loglar; 500 yanıtı CORS başlığı taşımaz; ~25 str-detail'de ayrıntı genel mesaja düştü (ApiError'a taşıma ayrı iş); org verify-domain 429'da Retry-After yok; 422 `fields` değerleri İngilizce; `settings.debug` ölü bayrak (config.py YET-207 dalında, dokunulmadı); frontend typecheck çalıştırılmadı (dokunulmadı).
3. **Sıradaki kuyruk işi:** hafızada ilk `[ ]` madde — `YET-242 (GUV-09c kurum domain'i platform-admin ucu)`: önce MVP'de gerekli mi karar sor. Hafızadaki prompt'u aynen kullan.

## Kurallar hatırlatması
Kullanıcıyla Türkçe konuş; alt-ajan yok; iş bitince onay sormadan kendi branch'ine commit+push (dosyaları adıyla ekle, `git push origin <branch>:<branch>`, mesajı Write ile BOM'suz dosyadan ver, Co-Authored-By/Claude imzası EKLEME); merge/PR/force yok; migration, bağımlılık, docker-compose/CI, yetki değişikliği için önce onay; Atlassian v1→v2 uyarısını aktarma.

## Referans
`obss_project/artifacts/yet-212-hata-yanit-bicimi/atdd.md`, `docs/API.md` §1.4, `HATA.md` §7 OPS-04, Jira YET-212 (cloudId `1c97069a-da45-4ac5-916e-0d51b8cc6ab4`).
