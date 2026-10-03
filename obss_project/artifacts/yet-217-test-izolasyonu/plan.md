# Plan — yet-217-test-izolasyonu
_Reference: atdd.md_

## Keşif bulguları (kanıtlı)
- Backend kök neden: testler `settings.database_url` ile dev DB'ye bağlanıyor. `create_engine(settings.database_url)` en az 8 test dosyasında modül seviyesinde + `app/core/deps.py:16` + `app/workers/outbox_worker.py`. `alembic/env.py:10` de aynı URL'yi kullanıyor. `Settings` ortam değişkenini `.env`'den önce okur (`app/core/config.py:13`).
  → Tek noktadan çözüm: `tests/conftest.py` en tepede, `app.*` import edilmeden ÖNCE `DATABASE_URL` ortam değişkenini test DB'sine çevirir. Tüm engine'ler (test + uygulama + alembic) otomatik test DB'sine gider; 8+ test dosyasını tek tek düzenlemek gerekmez.
- CI backend zaten izole: servis DB adı `test`, `alembic upgrade head` çalışıyor. Çözüm CI'da no-op olmalı (ad zaten `test` ile bitiyor).
- Frontend `evaluation.test.ts` (6): `submitEvaluation` → `getEngagement` (gerçek backend `apiFetch`) → ağ hatası. Test, eski localStorage-mock varsayımında.
- Frontend `evidence-upload-form` / `evaluation-form` (2): kod `messages.errors.generic` gösteriyor; `messages/tr.json:18` = "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin." Testler eski sabit metni ("Bir hata oluştu. Lütfen daha sonra tekrar deneyin.") bekliyor → **test bayat, kod doğru** (UI metni sabit metin dosyasından olmalı kuralı).
- Frontend `kurum/[id]/panel` "404 gösterilir (403 değil)": Jira/hafıza "aralıklı" diyor ama bu oturumda 4/4 kırık = **deterministik**. Test `queryByText(/erişiminiz|yetkin/i)` bekliyor; sayfa/alt bileşen büyük olasılıkla "Yetkin360"/"yetkinlik" içeren bir metin render ediyor. Kök neden teşhis edilecek (kod mu test regex'i mi).
- `frontend/package.json` `test: vitest run` var; CI'da çağrılmıyor.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/tests/conftest.py | Test DB türetme + oturum başı (drop/create + `alembic upgrade head`) + "_test" koruması. AC-1,2,3 | medium (tüm paketi etkiler) |
| frontend/lib/api/evaluation.test.ts | `vi.mock("./engagements")` ile ağdan bağımsız. AC-4 | low |
| frontend/app/calismalar/[id]/evidence-upload-form.test.tsx | Bayat metin yerine `messages.errors.generic`. AC-5 | low |
| frontend/app/calismalar/[id]/degerlendirme/evaluation-form.test.tsx | Aynı. AC-5 | low |
| frontend/app/kurum/[id]/panel/page.test.tsx (veya page.tsx) | Teşhise göre; AC-6 | low-medium |
| .github/workflows/ci.yml | frontend job'a `npm run test` ekle. AC-7 — **ONAY GEREKİR** | low |
| CONTRIBUTING.md | Test DB'si nasıl çalışır (AC-8) — doküman | low |

## New Files
Yok. (Test DB otomatik oluşturulur; ayrı script/compose eklenmez.)

## Tasarım (conftest)
1. Dosyanın en tepesinde (app import'tan önce): `DATABASE_URL` oku (env/`.env` — `.env` dosyası okunmaz, `Settings` zaten kendisi okur; URL'yi `sqlalchemy.engine.make_url` ile ayrıştırıp DB adını ayarlamak için `settings` değil `os.environ`/`TEST_DATABASE_URL` kullanılır; `.env`'deki değer için `Settings` import edilmeden önce değer gerekiyorsa `dotenv_values` yerine geçici import kullanılır — kod aşamasında karar, `.env` içeriği loglanmaz).
2. Ad `test` ile bitiyorsa olduğu gibi kullan (CI). Bitmiyorsa `<ad>_test` türet; `TEST_DATABASE_URL` varsa o öncelikli.
3. Session-scope autouse fixture: türetilmiş (yerel) durumda bakım DB'si (`postgres`) üzerinden AUTOCOMMIT ile `DROP DATABASE IF EXISTS` + `CREATE DATABASE`; sonra `alembic.command.upgrade(cfg, "head")`. CI'da (ad zaten test) drop yapma, sadece upgrade (idempotent).
4. Koruma: nihai DB adı `test` ile bitmiyorsa `RuntimeError` (atdd sözleşme satır 4/8).
5. Bağlanılamazsa açık mesaj (satır 2).

## Dependencies
- `alembic.command` / `alembic.ini` (backend/), `app.core.config.Settings`, mevcut migration zinciri (yalnız yeni test DB'sine uygulanır; üretim/dev DB'ye dokunulmaz, YENİ migration yok).
- `tests/authorization/conftest.py` (conftest zinciri; değişiklik sonrası toplanan test sayısı aynı kalmalı, AC-9).

## Migration Required?
Yeni migration: **Hayır.** Ancak mevcut migration'ların yeni test DB'sine `upgrade head` ile uygulanması gerekiyor → CLAUDE.md "migration uygulama = onay". **ONAY BEKLİYOR.**

## Risks
- Paket şu an seed'li dev DB'ye bağımlı olarak geçen 812 testin bir kısmı seed verisine (ör. 36 skill) güvenebilir; boş test DB'sinde yeni kırıklar çıkabilir. AC-2 bunu yakalar; çıkarsa kök neden test başına veri kurulumu (test kuralı: her test kendi verisini kurar), assert gevşetilmez.
- Gerçek-oturum testleri (`*_real_session`) commit eder → aynı koşu içinde test DB'sinde kalıntı bırakır; seed testleri "0 mevcut" varsayıyorsa sıra bağımlılığı çıkabilir. Çözüm gerekirse o testlerin temizliği (kendi verisi).
- `DROP DATABASE` açık bağlantı varken başarısız olur (önceki koşunun engine'i); `WITH (FORCE)` (PG ≥13, compose'ta PG16) kullanılır.
- Yerel DB rolünün `CREATEDB` yetkisi: compose'ta kullanıcı superuser (POSTGRES_USER) → sorun beklenmez.
- Panel testi kök neden kod tarafında çıkarsa 404 mesajı sızıntısı olabilir (güvenlik kuralı: 404, "yetkin yok" metni yok) → yetki bulgusu olarak bildirilir.

## Open Questions (kullanıcıya — karar gerektirir)
1. Test DB'sini otomatik oluşturup (drop/create) `alembic upgrade head` uygulamayı onaylıyor musunuz? (migration uygulama onayı)
2. Frontend düzeltmeleri + `ci.yml` değişikliği bu görevde mi (ben), Elif'e mi? `ci.yml` değişikliği onayı?
3. İki form testi için "kod doğru, test bayat" tespitiyle testteki metni `messages.errors.generic`'e bağlamak uygun mu? (testing.md: test kırıldıysa değiştirmeden önce sor.)
4. test_strategy 0/70/30 varsayımı.

## Kararlar
Henüz karar yok: açık sorular kullanıcının yetki alanında (onay gerektiren işlemler), Sonnet alt-ajanına devredilmedi.

## Not
Dosya türü: `.tsx` test dosyaları (görsel UI değil, DOM test) → `verify` gate 11 (`vision-test`) N/A.
