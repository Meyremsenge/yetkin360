# Plan — yet-9-organization-domain-dogrulama
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Kritik keşif — atdd.md'nin varsaydığından farklı gerçek durum

Kod tabanı taraması, atdd.md yazılırken bilinmeyen üç önemli gerçeği ortaya
çıkardı:

1. **`Organization` ve `OrganizationMember` modelleri zaten var**
   (`app/models/identity.py:109-144`, migration `b82aa928fbd2` ile
   oluşturulmuş — PLAN 1.1 kapsamında). Bu görev yeni tablo değil, yeni
   **uç + servis** eklemek.
2. **Rol enum'u `ADMIN|MEMBER`** (`ck_organization_members_role`), atdd.md'nin
   DOMAIN.md §3.4'ten aldığı `OWNER|SUPERVISOR|MEMBER` **değil**. DOMAIN.md
   muhtemelen ileri vizyon, gerçek uygulanmış şema daha basit. AC-S2 (rol
   yükseltme koruması) bu gerçek enum'a göre yeniden yazılmalı: `ADMIN`
   rolünü yalnızca mevcut bir `ADMIN` verebilir, `MEMBER` istenirse serbest.
3. **`can()`/`scoped_organizations()` zaten mevcut**
   (`app/services/authorization.py:66-68,78-94`), `Principal.org_ids` /
   `org_admin_ids` / `kind in ("ORG_MEMBER","ORG_ADMIN")` ile çalışıyor.
   Bu görev bunları **yeniden yazmaz**, olduğu gibi kullanır.
4. **Domain'de unique constraint yok** (`Organization.domain: CITEXT`,
   unique değil) — atdd.md'nin AC-9 (aynı domain iki organization'da T2
   olamaz) varsayımı hâlâ geçerli ama DB'de yeni bir **partial unique index**
   gerektiriyor (aşağıda Migration bölümü).
5. **`verify-domain` için gereken hiçbir kolon yok**: DNS TXT doğrulama
   token'ı saklamak ve rate-limit (`last_verify_attempt_at`) için yeni
   kolonlar gerekiyor — yeni migration şart.
6. **`institution.py` servisindeki `invite_member` hiç `outbox.enqueue()`
   çağırmıyor** (YET-8 kapsamında davet e-postası hiç kurulmamış). Bu görev
   organizations için outbox'u ilk kez bağlayacak — referans alınacak hazır
   bir çağrı örneği yok, `outbox.py`'nin kendi docstring'i ve PII guard'ı
   (`email` anahtarı outbox payload'ında **yasak**) rehber alınacak.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/authorization.py` | `AC-S2` rol-yükseltme kontrolü ve `AC-S6` (scoped erişim) zaten `scoped_organizations`/`can()` içinde karşılanıyor — **değişiklik gerekmeyebilir**, ama yeni `verify-domain`/`members` uçları için ek bir `action` (`"invite_member"` gibi) `can()`'a eklenmesi gerekip gerekmediği `code-copilot` aşamasında değerlendirilmeli. | medium |
| `backend/app/models/__init__.py` | Yeni `OrganizationMember`'ın (zaten `identity.py`'de var) export edilip edilmediği kontrol edilmeli; muhtemelen zaten export ediliyor, doğrulama gerekir. | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/services/organization.py` | İş mantığı: `create_organization`, `invite_org_member`, `verify_domain` — `institution.py`'nin kalıbı takip edilir (Exception sınıfları, `session.flush()`, upsert deseni). |
| `backend/app/api/organizations.py` | Router: `POST /organizations`, `POST /organizations/{id}/members`, `POST /organizations/{id}/verify-domain`, `GET /organizations/{id}` — `institutions.py`'nin kalıbı takip edilir (Pydantic DTO'lar, `get_current_principal`, `scoped_organizations`+`get_scoped_or_404`). |
| `backend/app/schemas/organization.py` | Eğer `api/organizations.py` içinde DTO'ları tutmak yerine (institutions.py örneğinde olduğu gibi router dosyasının içinde tutulmuş) ayrı şema dosyası tercih edilirse — **institutions.py örneğine uyup router içinde tutmak** tutarlılık için tercih edilir, bu dosya muhtemelen gerekmeyecek (Open Question'a bkz.). |
| `backend/tests/test_organizations.py` (test-copilot yazacak) | Bu görevin unit/integration testleri — `code-copilot`/`test-copilot` adımında. |
| `backend/tests/authorization/test_organizations_matrix.py` (test-copilot yazacak) | AC-S1/S2/S6 tenant-izolasyon test matrisi — `authz-test` skill'i kalıbına göre. |
| `backend/alembic/versions/<hash>_add_organization_domain_verification_columns.py` | Yeni migration — bkz. "Migration Required?". |

## Dependencies
- `app/api/deps.py` → `get_current_principal`, `get_session` (institutions.py ile aynı şekilde kullanılır).
- `app/services/authorization.py` → `Principal`, `can()`, `scoped_organizations()`, `get_scoped_or_404()` (mevcut, değiştirilmeyecek — sadece kullanılacak).
- `app/services/outbox.py` → `enqueue(session, topic, payload)` — üye daveti için. **Kritik kısıt:** `payload` içinde `email` anahtarı **kullanılamaz** (`_check_pii_in_payload` `ValueError` fırlatır) — davet edilecek kullanıcının `user_id`'si payload'a konur, worker gerekirse `user_id`'den e-postayı kendi sorgusuyla çeker.
- `app/services/audit.py` → `log_audit_event(...)` — AC-S7 (kurum oluşturma/üye davet/domain doğrulama olaylarının izi) için. Aynı kısıt: `metadata` içinde `email` anahtarı yasak.
- `app/models/identity.py` → `Organization`, `OrganizationMember` (mevcut modeller, değiştirilmeyecek — yalnız migration ile yeni kolon eklenecek).
- DNS sorgusu için yeni bir bağımlılık gerekebilir (`dnspython`) — **bağımlılık ekleme** CLAUDE.md'ye göre açık onay gerektirir, `code-copilot` aşamasından önce kullanıcıya sorulmalı (aşağıda Open Questions).

## Migration Required?
**Evet** — ama migration'ın kendisi CLAUDE.md kuralı gereği ("Migration
oluşturma veya uygulama... önce açık onay al") ve `.claude/rules/database.md`
("Migration oluşturmadan ve uygulamadan önce kullanıcıya sor") gereği
**kullanıcı onayı olmadan oluşturulmayacak**. İhtiyaç duyulan değişiklikler:

1. `organizations` tablosuna:
   - `domain_verification_token` (`String`, nullable) — DNS TXT için üretilen
     rastgele token.
   - `last_verify_attempt_at` (`timestamptz`, nullable) — rate-limit cooldown
     için.
2. Yeni **partial unique index**: `organizations(domain)` üzerinde
   `WHERE verification_level = 'T2' AND deleted_at IS NULL` koşuluyla —
   aynı domain'in birden fazla T2 kurumda doğrulanmasını DB seviyesinde
   engeller (AC-9/AC-9b, `.claude/rules/database.md`: "Kısıt veritabanında
   olur").

Bu üç değişiklik geriye uyumlu (yeni nullable kolon + yeni index, mevcut
veriyi bozmaz) — `.claude/rules/database.md`'nin "önce ekle" ilkesine uygun.

`alembic upgrade head` **ve** `alembic downgrade -1` ikisi de `verify`
adımında çalıştırılmalı.

## Risks
(atdd.md'den taşınan + keşifte bulunanlar)
- DNS mock/gerçek sorgu ayrımı test edilebilirliğini etkiler (atdd.md
  Risks'te zaten var).
- Rate-limit için DB tabanlı cooldown'da race condition riski (atdd.md
  Risks'te zaten var, "kabul edilen risk").
- **Yeni risk:** `outbox.enqueue()`'nin PII guard'ı `email` anahtarını
  reddettiği için, davet akışının payload şekli institutions.py'de HİÇ
  denenmemiş bir yol — `code-copilot` bunu ilk kez organizations için
  kuracak, dikkatli tasarlanmalı (`user_id` + `organization_id` yeterli,
  worker kendi sorgusuyla e-postayı bulur).
- **Yeni risk:** DOMAIN.md (§3.4) ile gerçek şema (rol enum'u) arasındaki
  tutarsızlık yalnız bu görevde değil, muhtemelen dokümantasyon genelinde
  var — bu görev kapsamında yalnız `atdd.md`/`plan.md` gerçek şemaya göre
  düzeltildi, `docs/DOMAIN.md`'nin kendisi güncellenmedi (kapsam dışı,
  ayrı bir dokümantasyon-senkronizasyon görevi gerektirir).

## Open Questions
1. **Rol enum'u:** atdd.md `OWNER|SUPERVISOR|MEMBER` varsaydı, gerçek DB
   kısıtı `ADMIN|MEMBER`. Hangisiyle devam edilsin — mevcut `ADMIN|MEMBER`
   enum'una sadık mı kalınsın (migration gerektirmez), yoksa üç rollü
   sisteme geçmek için **yeni bir migration ile enum genişletilsin mi**
   (ek onay + ek risk)?
2. **DNS sorgusu gerçek mi mock mu:** `dnspython` bağımlılığı eklenip
   gerçek DNS TXT sorgusu mu yapılsın (CLAUDE.md: bağımlılık ekleme açık
   onay gerektirir), yoksa hackathon/MVP kapsamında `verify-domain`
   çağrısının DNS sorgusu **manuel/simüle** mi kalsın (ör. sabit bir
   test-only doğrulama mekanizması)?
3. **Migration onayı:** Yukarıdaki "Migration Required?" bölümündeki 3
   değişiklik (`domain_verification_token`, `last_verify_attempt_at`,
   partial unique index) oluşturulup uygulansın mı?
4. **DTO dosya yeri:** `institutions.py` örneğinde Pydantic DTO'lar router
   dosyasının içinde tutuluyor (ayrı `schemas/institution.py` yok). Aynı
   kalıp mı takip edilsin (öneri: evet, tutarlılık için), yoksa
   `schemas/organization.py` ayrı mı açılsın?

Kullanıcıdan yanıt/"sen karar ver" bekleniyor — `test-copilot`'a bu sorular
çözülmeden geçilmeyecek.

## Kararlar
(kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı)

1. **Rol enum'u:** Mevcut `ADMIN|MEMBER` ile devam. DOMAIN.md'nin
   `OWNER|SUPERVISOR|MEMBER` varsayımı ileri vizyon; gerçek şemayı
   genişletmek MVP kapsamı dışı ek migration+risk gerektirir. `atdd.md`
   güncellenecek: AC-S2 "rol yükseltme" kriteri `ADMIN` yalnızca mevcut
   `ADMIN` tarafından verilebilir şeklinde kalır (zaten bu şekilde
   uyarlanmıştı).
2. **DNS sorgusu:** Gerçek `dnspython` ile gerçek DNS TXT sorgusu yapılır,
   resolver çağrısı test edilebilirlik için mock'lanabilir bir arayüz
   arkasına konur (ör. `verify_domain(..., resolver=dns.resolver)`).
   Gerekçe: atdd.md AC-7/AC-8 ve performance_target ("<3s") gerçek bir DNS
   sorgusunu varsayıyor; simülasyon bu kriterleri anlamsızlaştırır.
   **Not:** `dnspython` bağımlılık eklemedir — CLAUDE.md gereği bu, `plan`
   aşamasının verdiği genel yetkiyle sınırlı kalmaz, `code-copilot`
   başlamadan hemen önce kullanıcıya ayrıca ve açıkça sorulacak.
3. **Migration:** Üç değişiklik (nullable `domain_verification_token`,
   nullable `last_verify_attempt_at`, partial unique index) onaylandı —
   AC-9/AC-9b ve AC-S4 bunlar olmadan test edilemez. **Not:** Bu karar
   migration'ın *içeriğini* onaylar; CLAUDE.md'nin "migration oluşturma/
   uygulama önce açık onay" kuralı gereği, `code-copilot` fiilen
   `alembic revision`/`alembic upgrade` çalıştırmadan hemen önce kullanıcıya
   bu spesifik komutla tekrar kısaca bildirim yapılacak (tam onay isteği
   değil, "şimdi şu migration'ı oluşturup uyguluyorum" bilgilendirmesi —
   içerik zaten burada onaylandığı için).
4. **DTO dosya yeri:** `institutions.py` kalıbına uyulup DTO'lar
   `api/organizations.py` router dosyasının içinde kalır — ayrı
   `schemas/organization.py` açılmaz. `plan.md`'nin "New Files" tablosundaki
   `schemas/organization.py` satırı bu kararla **iptal edilmiştir**.
