# Plan — yet-5-outbox-worker
_Reference: atdd.md_

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | Yeni `Outbox` modelini export listesine ekle (mevcut desen: `AuditEvent`, `RefreshToken` gibi) | low |
| `backend/app/services/auth.py:108-154` | `register_user()` içindeki duplicate-email TODO'sunu (satır 118-121) `outbox_service.enqueue(...)` çağrısına bağla — AC-3 | low |
| `docs/ENV.md` §6 | `OUTBOX_POLL_INTERVAL_SECONDS`, `OUTBOX_MAX_ATTEMPTS` değişkenlerini tabloya ekle (mevcut `EMAIL_BACKEND` deseniyle tutarlı) | low |
| `.env.example` | Aynı iki değişkenin placeholder'ı — **erişim engellendi, bkz. Open Questions** | low (ama erişilemedi) |

## New Files

| File | Purpose |
|------|---------|
| `backend/app/models/outbox.py` | `Outbox` ORM modeli: `id bigserial PK`, `topic text NOT NULL`, `payload jsonb NOT NULL`, `created_at`, `processed_at nullable`, `attempts int default 0`. `app/models/audit.py`'deki bigserial-PK desenine paralel ama **immutability trigger yok** (mutable — `processed_at`/`attempts` worker tarafından UPDATE edilir). `app/models/auth.py`'deki gibi TimestampMixin kullanılmaz (audit.py gibi elle `created_at` — outbox'ta `updated_at` gerekmiyor, sadece `processed_at`/`attempts` değişir). |
| `backend/alembic/versions/<hash>_add_outbox_table.py` | `outbox` tablosu + partial index `(created_at) WHERE processed_at IS NULL` (docs/DATABASE.md §2). `down_revision = 'ffcf10979a51'` (mevcut head). Ham SQL yalnız burada (partial index `op.create_index` ile `postgresql_where` kullanılarak, CREATE TABLE gerekmiyor çünkü immutability trigger yok — düz `op.create_table`/`op.create_index` yeterli, `op.execute` gerekmez). |
| `backend/app/services/outbox.py` | `enqueue(session, topic, payload)` — AC-1, AC-7 (AC-S1): `audit.py`'deki `_check_pii_in_metadata` guard'ının aynısı payload'a da uygulanır (aynı sensitive-keys seti + case-insensitive + nested dict taraması — kod tekrarını önlemek için `audit.py`'den import edilip paylaşılabilir mi, yoksa outbox'a özgü mü kopyalanmalı, **Open Question**). Senkron, sadece `session.add()` + `session.flush()` — ağ çağrısı yok. |
| `backend/app/workers/__init__.py` | Yeni paket (worker'ın kendi klasörü — `app/api`, `app/services` ile aynı seviyede, final analiz §39 mimari dizin yapısına uygun: `workers/ outbox_processor, file_scanner`). |
| `backend/app/workers/outbox_worker.py` | Polling döngüsü (AC-2, AC-4, AC-5, AC-6, AC-8/AC-S2): `SELECT ... FOR UPDATE SKIP LOCKED` ile batch seçim (`WHERE processed_at IS NULL AND attempts < OUTBOX_MAX_ATTEMPTS ORDER BY created_at`), topic→handler dispatch tablosu, her satır kendi transaction'ında işlenir, başarılıysa `processed_at=now()`, hata yakalanırsa `attempts += 1` + log (payload'sız). İlk handler: `email.duplicate_registration_attempt` → `EMAIL_BACKEND=console` ise konsola yaz (docs/ENV.md §6). `if __name__ == "__main__":` ile çalıştırılabilir script (systemd unit dosyası bu görevin kapsamı dışı — atdd.md Assumptions). |
| `backend/tests/test_outbox_service.py` | `enqueue()` unit testleri: happy path (AC-1), PII guard (AC-S1: password/password_hash/email/token/private_note, nested, case-insensitive — `test_audit_events.py`'deki testlerle simetrik). |
| `backend/tests/test_outbox_worker.py` | Worker integration testleri (gerçek Postgres, `test_audit_events.py`'deki `session` fixture pattern'i — `engine = create_engine(settings.database_url)`, transaction+rollback): satır seçme/işaretleme (AC-2), attempts artırma (AC-4), max-attempts sonrası dışlanma (AC-5), `SKIP LOCKED` ile çift-işleme önleme (AC-6, iki ayrı connection/session ile simüle edilir), log'da payload sızmaması (AC-S2 — `caplog` ile). |
| `backend/tests/test_migration.py` (mevcut dosyaya ekleme, yeni dosya değil — **Open Question**: yeni migration'a özel bir test mi gerekir, yoksa mevcut `test_migration.py`'nin genel upgrade/downgrade testi yeterli mi?) | `alembic upgrade head` + `alembic downgrade -1` doğrulaması (CLAUDE.md doğrulama matrisi: "Veritabanı şeması / migration" satırı zorunlu kılıyor). |

## Dependencies

- `app/core/config.py` — `Settings` sınıfına `outbox_poll_interval_seconds: int = 5`, `outbox_max_attempts: int = 5`, `email_backend: str = "console"` alanları eklenmeli (şu an bu üçü `Settings`'te yok, sadece docs/ENV.md'de var — worker'ın çalışması için gerçek Pydantic alanları gerekir). **Bu, atdd.md'nin "Etkilenen Dosyalar" listesinde yoktu — plan aşamasında bulundu, aşağıda Open Questions'a eklendi.**
- `app/services/audit.py` içindeki `_check_pii_in_metadata` — outbox servisi bu fonksiyonu ya import edip yeniden kullanmalı ya da kendi kopyasını tutmalı (modüller birbirinin iç dosyalarını import etmez kuralı: `audit.py` `services/` içinde, `outbox.py` da `services/` içinde olacağı için aynı katman — CLAUDE.md'nin yasakladığı "modüller birbirinin iç dosyalarını import etmez" kuralı muhtemelen `app/api`, `app/services`, `app/models` gibi üst seviye modüller arası import için, aynı `services/` paketi içi paylaşım için değil; yine de netleştirilmeli).
- `app/models/base.py` — `Base` sınıfı, outbox modelinin de miras alacağı taban.
- `docs/DATABASE.md` §2, §5 — şema ve transaction sınırı referansı zaten atdd.md'ye taşındı.

## Migration Required?

**Evet.** Yeni `outbox` tablosu (CLAUDE.md: "Migration oluşturma veya uygulama" → **önce açık onay al** listesinde). Bu plan migration'ı *tanımlıyor* ama `code-copilot`/`test-copilot` aşamasına geçmeden **migration oluşturma ve uygulama için kullanıcıdan ayrıca onay alınmalı** — bu onay atdd.md/plan.md onayından ayrı, CLAUDE.md'nin "İzin ve onay sınırları" bölümünde açıkça listelenmiş bir kalem.

İçerik: `op.create_table('outbox', ...)` + `op.create_index(..., postgresql_where=sa.text('processed_at IS NULL'))`. `down_revision='ffcf10979a51'` (mevcut head, doğrulandı). Immutability trigger YOK — `audit_events` migration'ının aksine bu migration sade bir `create_table`/`create_index` çifti.

## Risks

atdd.md'den taşınan + plan aşamasında bulunan:
- **PII retention riski** (atdd.md'den taşındı) — kabul edilen risk, değişmedi.
- **Config alanları eksik** (yeni bulgu): `Settings` sınıfına 3 yeni alan eklenmesi gerekiyor; `secret_key` gibi zorunlu alanlar `.env`'den okunuyor, yeni alanların varsayılan değerleri var (`= 5`, `= "console"`) olduğu için `.env`'e dokunmadan da çalışır — ama `.env.example`'a placeholder eklenmemesi (erişim engeli nedeniyle) dokümantasyon tutarsızlığı yaratır.
- **`.env.example` erişimi bu oturumda engellendi** — CLAUDE.md'nin ".env, secrets/ okuma veya commit'leme" kesin yasağı `.env.example`'ı kapsamıyor olmalı (placeholder dosyası, sır içermiyor) ama harness izni reddetti. `code-copilot`/`test-copilot` aşamasında da aynı engelle karşılaşılabilir — kullanıcıya bu görev başlamadan bildirilmeli.

## Open Questions

1. **`Settings` sınıfına yeni alanlar eklemek migration/config değişikliği sayılır mı?** `app/core/config.py` "Yetkilendirme, kimlik doğrulama veya izin mantığı değişikliği" ya da genel dosya değişikliği kapsamında mı — CLAUDE.md'nin "Var olan dosyayı değiştirmeden önce ne değişeceğini tek cümleyle söyle" kuralı yeterli görünüyor (config.py bu üç özel onay kategorisinden hiçbirine girmiyor), ama teyit edilmeli.
2. **`_check_pii_in_metadata` paylaşımı** — `outbox.py` kendi kopyasını mı tutsun yoksa `audit.py`'den mi import etsin? Kod tekrarını önlemek cazip ama CLAUDE.md "Modüller birbirinin iç dosyalarını import etmez" kuralının tam kapsamı (aynı `services/` paketi içi mi, yoksa `app/api`↔`app/services`↔`app/models` gibi üst seviye mi) atdd.md'de netleşmedi.
3. **`.env.example` erişim engeli** — bu oturumda Grep/Bash ile `.env.example`'a erişim reddedildi. `code-copilot` bu dosyayı değiştirmeye çalıştığında aynı engelle karşılaşabilir; kullanıcıya önceden sorulmalı (belki kullanıcı dosyayı kendisi düzenleyecek, ya da izin farklı bir modda verilecek).
4. **Yeni migration testi ayrı dosya mı, mevcut `test_migration.py`'ye ekleme mi?** Mevcut dosya okunmadı (kapsam dışı bırakıldı — CLAUDE.md "aynı dosyayı iki kez okuma" ilkesi burada "gereksiz dosya okuma" ile çakışmadı çünkü hiç okunmadı); `test-copilot` bu dosyayı açıp desenini görüp karar vermeli.

Yukarıdaki 4 soru **Sonnet 5 low alt-ajanına dispatch edildi** (aşağıya kararlar eklendi):

### Kararlar (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
1. **Config alanları:** Özel onay kategorisi değil — `config.py`'ye yeni `Settings` alanı eklemek CLAUDE.md'nin listelediği 6 özel-onay kalemine (migration, silme, 3+ dosya refactor, bağımlılık, auth/yetki mantığı, settings.json/docker-compose/CI) girmiyor; sadece "var olan dosyayı değiştirmeden önce ne değişeceğini tek cümleyle söyle" genel kuralı yeterli.
2. **PII guard paylaşımı:** `outbox.py` kendi kopyasını tutmalı — CLAUDE.md'nin "modüller birbirinin iç dosyalarını import etmez" kuralı dosya adı düzeyinde değil *modül* (feature) düzeyinde yorumlanmalı; `audit` ve `outbox` farklı feature'lar olduğu için `services/audit.py` içindeki private (`_` önekli) bir fonksiyonu `services/outbox.py`'nin import etmesi, iki modülü birbirine bağımlı kılar (audit.py'de yapılacak bir değişiklik outbox'ı sessizce etkiler). Küçük bir fonksiyon (~15 satır) olduğu için kopyalamanın maliyeti düşük, bağımsızlığın değeri yüksek.
3. **`.env.example` erişim engeli:** Bu görevde `.env.example` güncellemesi atlanır, `docs/ENV.md` güncellemesi yeterli kabul edilir; kullanıcıya `code-copilot`/`test-copilot` öncesi tek satır not düşülür ki aynı engelle karşılaşırlarsa şaşırmasınlar.
4. **Migration testi:** Yeni ayrı dosya değil, mevcut `test_migration.py`'ye eklenmeli — `test_migration.py` zaten "genel upgrade/downgrade" testi amacıyla var (dosya adından çıkarım), yeni bir tabloya özel ayrı bir dosya açmak gereksiz parçalanma yaratır; `test-copilot` dosyayı açtığında mevcut deseni takip edip ekleme yapmalı.

## Sonraki Adım
`plan.md` hazır. Sıradaki adım **`test-copilot`** (test-first — red adımı): yukarıdaki "Files to Modify" / "New Files" listeleri, atdd.md'yi tekrar yorumlamak yerine doğrudan dosya kapsamı olarak kullanılmalı. `code-copilot` bundan sonra, başarısız testler zaten var olduğunda çalışır.

**Kullanıcı onayı gereken kalem (CLAUDE.md izin sınırları):** Migration oluşturma/uygulama `test-copilot`/`code-copilot` sürecinde gerçekleşecek — bu, ayrı bir açık onay gerektiriyor, plan onayı bunu kapsamaz.
