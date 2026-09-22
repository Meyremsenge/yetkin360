# Plan — yet-7-user-talent-profili
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Kritik keşif — mevcut kodda dokümante edilen sözleşmeye uyulmadığı bulundu

`app/main.py:25-37`'deki global `api_error_handler`, `docs/API.md` §1.4'ün
belgelediği hata gövdesini (`{"code": "SCREAMING_SNAKE_CASE", "message":
"Türkçe", "request_id": ...}`) uygulamaya çalışıyor — `HTTPException.detail`
bir `dict` VE içinde `"code"` varsa **olduğu gibi** döner, aksi halde
(`detail` düz bir string ise) `{"code": "HTTP_ERROR", "message": str(detail),
"request_id": None}` şeklinde sarmalıyor.

AMA mevcut `institutions.py`/`organizations.py` (YET-8/YET-9) **hiçbiri** bu
sözleşmeye uymuyor — hepsi `HTTPException(status_code=409, detail="DOMAIN_TAKEN")`
gibi düz string `detail` kullanıyor. Sonuç: gerçek yanıt gövdesi
`{"code":"HTTP_ERROR","message":"DOMAIN_TAKEN","request_id":null}` oluyor —
API.md'nin öngördüğü anlamlı `code` (`DOMAIN_TAKEN` gibi) hiç dönmüyor,
her hata `"HTTP_ERROR"` kodu altında geliyor. Bu, `docs/API.md` §1.4'ün
fiilen ihlal edildiği anlamına geliyor (dokümantasyon-kod tutarsızlığı,
YET-9'da role enum'unda gördüğümüz DOMAIN.md tutarsızlığının bir benzeri).

**Bu YET-7'yi doğrudan etkiliyor** çünkü atdd.md'nin Davranış Sözleşmesi
tablosu hata gövdelerini `{"detail": "SLUG_TAKEN"}` gibi yazmıştı (mevcut
YET-8/YET-9 kalıbını taklit ederek) — bu, dokümante edilen gerçek sözleşmeye
(`{"code": "SLUG_TAKEN", "message": "...", "request_id": ...}`) uymuyor.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/main.py` | Yeni router'ı (`talent_router` veya `me_router`) `include_router` ile kaydetmek gerekecek. | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/api/me.py` | Router: `GET /me`, `PATCH /talents/me` — tek dosyada iki farklı path (prefix yok, `@router.get("/me")` + `@router.patch("/talents/me")`), DTO'lar router içinde (institutions.py kalıbı — ama hata gövdesi için aşağıdaki Open Question'a bkz.). |
| `backend/app/services/talent.py` | İş mantığı: `get_me_context(user, session)`, `update_talent_profile(principal, payload, session)` — `institution.py`/`organization.py` kalıbı (Exception sınıfları, `session.flush()`/`commit()` sırası). |
| `backend/tests/test_talent.py` | Fonksiyonel AC testleri (test-copilot yazacak). |
| `backend/tests/test_talent_authorization.py` | AC-S1/S2/S3/AC-8 tenant/kendi-veri izolasyon testleri (test-copilot yazacak). |

## Dependencies
- `app/api/deps.py` → `get_current_principal`, `get_session` (institutions.py/organizations.py ile aynı).
- `app/services/authorization.py` → `Principal`, `scoped_talent_profiles()`,
  `get_scoped_or_404()` — **AC-8/atdd.md'nin işaretlediği düzeltme burada
  yapılacak:** `scoped_talent_profiles()`'ın koşulu `principal.kind ==
  "TALENT"` yerine `principal.talent_id is not None` olacak şekilde
  değiştirilecek. Bu bir **yetkilendirme mantığı değişikliği** — atdd.md'nin
  Hard Stop onayında (kullanıcı "devam" dedi, atdd.md bu değişikliği AC-8
  olarak açıkça listelemişti) zaten onaylandı, `code-copilot` başlamadan
  ayrıca tekrar sorulmayacak ama değişiklik küçük ve tek satırlık olacak
  (mevcut fonksiyonun geri kalanı aynı kalır).
- `app/models/identity.py` → `User`, `TalentProfile` (mevcut, DEĞİŞTİRİLMEZ).
- `app/main.py`'nin `api_error_handler`'ı → **DEĞİŞTİRİLMEZ**, ama yeni
  endpoint'lerin `HTTPException`'ları bu handler'ın "geç" (pass-through)
  koluna düşecek şekilde `detail={"code": ..., "message": ...}` dict olarak
  fırlatılması gerekiyor (Open Question 1'e bkz.).

## Migration Required?
**Hayır** — `TalentProfile`/`User` modelleri ve kolonları zaten YET-1'de
oluşturuldu, şema değişikliği gerekmiyor.

## Risks
(atdd.md'den taşınan + keşifte bulunan)
- `scoped_talent_profiles()` değişikliği dar kapsamlı olsa da yetkilendirme
  dosyasına dokunuyor — `code-copilot` sonrası **mutlaka**
  `pytest tests/authorization -q` tam paketi çalıştırılmalı (CLAUDE.md
  doğrulama matrisi: "Yetkilendirme/kimlik doğrulama → tüm paket").
- `public_slug` unique constraint'e güvenip önce `SELECT` ile kontrol etmek
  race condition'a açık (atdd.md'de zaten not edilmiş, MVP için kabul
  edilebilir).
- **Yeni risk (bu adımda bulundu):** Eğer Open Question 1'e "evet, doğru
  sözleşmeyi kullan" cevabı verilirse, YET-7'nin hata gövdeleri
  YET-8/YET-9'dakinden **farklı** görünecek (`code` alanı anlamlı olacak,
  onlarda `"HTTP_ERROR"` kalacak) — bu bilinçli bir tutarsızlık, ayrı bir
  "geçmiş uçları API.md'ye uydur" görevi gerektirir (bu görevin kapsamı
  dışı, `postmortem`'e not düşülebilir).

## Open Questions

1. **Hata gövdesi sözleşmesi:** YET-7'nin yeni uçları `docs/API.md` §1.4'ün
   dokümante ettiği gerçek sözleşmeye (`HTTPException(detail={"code":
   "SLUG_TAKEN", "message": "Bu kısa bağlantı zaten kullanılıyor",
   "request_id": None})`) mi uysun, yoksa mevcut YET-8/YET-9 kalıbını
   (düz string `detail`, fiilen `"HTTP_ERROR"` koduna sarmalanan) mı takip
   etsin (tutarlılık için, ama dokümantasyona aykırı)? **Öneri: doğru
   sözleşmeyi kullan** — yeni kod dokümante edilen kontratı ihlal etmemeli,
   geçmiş tutarsızlık ayrı bir borç olarak kalsın.
2. **Router dosya adı/yapısı:** `/me` ve `/talents/me` farklı path'ler
   (ortak prefix yok) — tek `app/api/me.py` dosyasında `prefix=""` ile iki
   endpoint mi (öneri, CAVEMAN — tek dosya, az dosya), yoksa `app/api/talents.py`
   ayrı mı açılsın (gelecekte `GET /talents/{id}`, skills uçları buraya
   ekleneceği için, ama onlar PLAN 1.11+ kapsamında, bu görevde YOK)?
   **Öneri: `app/api/me.py`, tek dosya** — YAGNI, gelecekteki genişleme
   ayrı görevde ayrı dosyaya taşınabilir.

Kullanıcıdan yanıt/"sen karar ver" bekleniyor.

## Kararlar
1. **Hata gövdesi sözleşmesi:** Kullanıcı onayladı — YET-7 `docs/API.md`
   §1.4'ün gerçek sözleşmesini kullanacak: `HTTPException(status_code=...,
   detail={"code": "SLUG_TAKEN", "message": "...", "request_id": None})`.
   Mevcut YET-8/YET-9 kalıbı (düz string detail) taklit EDİLMEYECEK.
2. **Router dosya adı/yapısı:** Kullanıcı açıkça yanıtlamadı, öneri
   (`app/api/me.py`, tek dosya, YAGNI) uygulanacak — düşük riskli/geri
   döndürülebilir bir mimari tercih, itiraz gelmedi.
