Frontend-pipeline: tetikleyici yok (backend-only görev — `.tsx`/`.jsx`/`.css` dokunulmuyor, atdd.md'de "Görsel/UI kriteri" boş).

# Plan — guv-02-davet-yaniti-duzeltmesi
_Reference: atdd.md_

## Keşif Bulguları (gerçek repo durumu)

- **`app/core/errors.py`**: `ApiError(HTTPException)` zaten var — `{code, message, request_id}` şeklini üretiyor. Organizations.py şu an bunu KULLANMIYOR (ham `HTTPException` kullanıyor) — bu görev ikisini de `ApiError`'a geçirmeli (AC-3, AC-7, AC-8).
- **`app/services/organization.py:30`**: `class AlreadyMemberError(Exception)` zaten var. AC-4 gereği bu artık router'da farklı bir yanıta (409) DEĞİL, aynı `202 queued`'a çevrilecek — servis katmanında exception hâlâ fırlatılabilir ama router onu 409 yerine 202'ye map edecek (ya da servis katmanı hiç exception fırlatmayıp "no-op" olduğunu bir bayrakla dönecek — code-copilot karar verecek, ikisi de davranış sözleşmesini karşılar).
- **`app/services/outbox.py:64` `enqueue()`**: Aynı transaction içinde satır ekliyor (atomiklik garantili — atdd.md'nin Rollback Beklentisi'ni doğruluyor). **PII guard** var: payload'da `email`/`password`/`token`/`private_note`/`password_hash` anahtarları varsa `ValueError` fırlatıyor — audit/outbox payload'larına ASLA ham e-posta konulmamalı (zaten atdd.md AC-2/AC-6 bunu gerektiriyor, kod bunu ayrıca zorluyor).
- **`docs/API.md`**: `POST /organizations/{id}/members` zaten dokümante (satır 303) — `201` + `404`/`409 ALREADY_MEMBER` diyor, bu görevle **değişecek** (`202` + numaralandırma kapalı). `POST /institutions/{id}/members` ise **hiç dokümante değil** — bu görev onu da ekleyecek. Emsal: `POST /institutions/{id}/reminders` (satır 320) zaten `202 — queued_count` döndürüyor — bizim `202 {"status":"queued"}` tasarımımız projenin var olan konvansiyonuyla tutarlı.
- **`app/api/institutions.py`**: Şu an `log_audit_event`, `enqueue`, `ApiError` HİÇ import edilmiyor (yalnız `HTTPException` var). AC-6 (audit ekleme) ve tutarlı hata biçimi için bu üç import eklenmeli — organizations.py'deki mevcut kullanım deseni (satır ~270-290) birebir örnek alınabilir.
- **`app/services/institution.py:80-128` `invite_member()`**: Şu an UPSERT yapıyor (`if member: member.role = role`). AC-4/AC-5 gereği bu dal kaldırılacak — mevcut üye varsa hiçbir şey değiştirmeden "zaten üye" durumunu router'a bildirecek (ör. yeni bir `AlreadyMemberError` fırlatarak, organization.py'deki gibi — tutarlılık için aynı exception sınıfı `app/services/organization.py`'den import edilebilir ya da institution.py'ye kendi eşdeğeri eklenir; code-copilot en basit olanı seçmeli — CAVEMAN).
- **`app/models/identity.py:67`**: `CheckConstraint("role IN ('ADMIN','COORDINATOR')", name="ck_institution_members_role")` — DB kısıtı zaten doğru. Pydantic `Literal` eklenince bu constraint'e artık hiç düşülmeyecek (savunma katmanı olarak kalıyor, CLAUDE.md "kısıtlar veritabanında olur" kuralına uygun, dokunulmuyor).
- **DÜZELTME (kod keşfinden sonra bulundu — plan yazıldıktan sonra):** `backend/app/main.py:60-82`'deki `validation_exception_handler` (Pydantic `RequestValidationError` için) yanıtı `{"code": "VALIDATION_ERROR", ...}` ile üretiyor — `api_error_handler` (satır 45-57, manuel `HTTPException`/`ApiError` için) ise `exc.detail`'deki `code`'u olduğu gibi geçiriyor. **`InstitutionMemberInvite`/`OrganizationMemberInvite`'ın `role` alanını Pydantic `Literal`'a çevirmek YANLIŞ** — bu, framework-seviyesi bir `RequestValidationError` üretir ve yanıt kodu `VALIDATION_ERROR` olur, ama atdd.md AC-3 ve şimdi yazılan testler tam eşleşmeyle `"INVALID_ROLE"` bekliyor. **Rol validasyonu, organizations.py'nin zaten yaptığı gibi (satır 236-237) handler içinde ELLE kalmalı**: `if payload.role not in (...): raise ApiError(422, "INVALID_ROLE", "...")`. Pydantic alanı `role: str` olarak kalır (Literal'a çevrilmez), yorum satırı korunur.
- Migration gerekmiyor — hiçbir yeni kolon/tablo yok, atdd.md'nin "Kapsam Dışı" bölümüyle tutarlı.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/api/organizations.py` | AC-1/2/4/7: yanıt `201→202`, `ApiError` kullanımı, `AlreadyMemberError`'ın artık 409 değil no-op+202 üretmesi, mevcut 500 yolu (ValueError yakalanmıyor) kapatılacak | medium |
| `backend/app/api/institutions.py` | AC-1/2/3/4/6/8: `role` alanı `Literal`, `log_audit_event`+`enqueue` eklenmesi, UPSERT'in kaldırılmasına uyum, `ApiError` kullanımı, yanıt `201→202` | high (şu an hiç audit/outbox yok, en çok yeni kod eklenen dosya) |
| `backend/app/services/organization.py` | AC-2: bilinmeyen e-postada artık `ValueError` yerine router'ın 202'ye çevirebileceği bir sinyal (ör. aynı exception, router'da farklı map) | medium |
| `backend/app/services/institution.py` | AC-3/4/5: rol validasyonu servise de eklenir (savunma katmanı, router zaten elle `if role not in (...)` ile engelliyor — bkz. düzeltme notu yukarıda), UPSERT dalı kaldırılır | high (davranış değişikliği: artık rol değiştirmiyor) |
| `docs/API.md` | AC bağımsız ama zorunlu: satır 303'teki org member sözleşmesi güncellenir, institution member ucu (hiç yoktu) eklenir | low |
| `backend/tests/authorization/test_organization_authorization.py` | AC-7 regresyon testi (tenant izolasyonu) — test-copilot'un işi, burada sadece dosya hedefi olarak not | — |
| `backend/tests/authorization/test_institution_authorization.py` | AC-8 regresyon testi — aynı şekilde | — |

## New Files
(Yok.)

## Dependencies
- `app.core.errors.ApiError` — her iki router'da tutarlı hata biçimi için.
- `app.services.outbox.enqueue` — institution tarafına yeni ekleniyor (PII guard'a dikkat: payload'a e-posta konulmayacak, `user_id` kullanılacak — organizations.py'deki mevcut desen zaten `user_id` kullanıyor, örnek alınmalı).
- `app.core.audit.log_audit_event` (veya projenin gerçek modül yolu — organizations.py'nin import satırından teyit edilecek) — institution tarafına yeni ekleniyor.
- `app.services.organization.AlreadyMemberError` — institution tarafında da kullanılabilir (tekrar tanımlamak yerine import etmek DRY olur, ama modüller birbirinin iç dosyasını import etmesin kuralına dikkat — CLAUDE.md "Modüller birbirinin iç dosyalarını import etmez" diyor; `organization.py` ve `institution.py` ayrı modüller sayılıyorsa institution.py kendi `AlreadyMemberError`'ını tanımlamalı. code-copilot bu kuralı gözetmeli.)

## Migration Required?
Hayır — yeni kolon/tablo yok, mevcut CHECK constraint (`ck_institution_members_role`) zaten doğru, dokunulmuyor.

## Risks
- (atdd.md'den taşındı) Yanıt süresi farkı tam eşitlenmiyor — kabul edilen risk.
- (atdd.md'den taşındı) Hız sınırı yok — ayrı görev (A-10).
- (yeni) `docs/API.md`'nin satır 303'ü değiştirilirken bu uca bağımlı başka bir dokümantasyon/test referansı olup olmadığı kontrol edilmeli — `plan` aşamasında `docs/API.md` dışında bu uca referans veren başka bir yer bulunmadı (yalnız satır 303), ama `code-copilot` değişiklik yaparken emin olmalı.
- (yeni) `AlreadyMemberError`'ın modüller-arası import kuralına takılma riski (yukarıda Dependencies'de not edildi) — code-copilot'a açıkça iletilmeli.

## Open Questions
(Boş — atdd.md'nin tek açık varsayımı ["zaten üye" → 202 mi 409 mu] kullanıcı tarafından "devam" onayıyla zaten kabul edildi; kod keşfi yeni bir belirsizlik ortaya çıkarmadı, yalnızca "hangi exception sınıfı kullanılacak" gibi code-copilot'un CAVEMAN ilkesiyle kendi kararını verebileceği küçük bir uygulama detayı kaldı, kullanıcıya sorulacak boyutta değil.)
