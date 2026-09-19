---
task_slug: yet-1-ilk-migration
jira_id: YET-1
saga_task_id: null
threat_model: not-applicable
priority: critical
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 70
  e2e: 10
affected_modules:
  - backend/app/models/ (yeni SQLAlchemy modelleri)
  - backend/alembic/versions/ (yeni migration dosyası)
  - backend/tests/test_migration.py (yeni)
---

# ATDD — yet-1-ilk-migration

## Jira Kaynağı
[YET-1 — İlk migration: user, talent, institution, organization, membership, skill](https://kuyusuzyusuf123.atlassian.net/browse/YET-1)

User Story (Jira'dan birebir): "As a backend developer, I want the initial Alembic migration for core entities (user, talent, institution, organization, membership, skill), so that all Faz 1 features have a real database foundation to build on."

Not: Jira özetindeki "membership" tekil ismi, gerçek şemada (docs/DATABASE.md) iki ayrı tabloya karşılık geliyor: `institution_members` ve `organization_members`. Bu görev toplam **7 tablo** oluşturur.

Bağımlılıklar (Jira issue links): `YET-1` hiçbir görev tarafından bloklanmıyor (hemen başlanabilir); `YET-1` şunları bloklar: `YET-2, YET-4, YET-7, YET-8, YET-9, YET-10, YET-11, YET-15`.

## Persona
Backend geliştirici (bu görevi alan kişi) — doğrudan son kullanıcıya görünmez. Faz 1'in kritik yolundaki temel taşı: `YET-2` (yetkilendirme), `YET-4` (auth) ve tüm CRUD görevleri (`YET-7/8/9/10/11`) bu migration'ın üzerine inşa edilecek.

## Hedef (Neden)
docs/DOMAIN.md ve docs/DATABASE.md'de tasarımı zaten kesinleşmiş 7 çekirdek tabloyu (users, institutions, institution_members, talent_profiles, organizations, organization_members, skills) gerçek bir Alembic migration'ına dönüştürmek — Faz 1'deki hiçbir uç, yetkilendirme kuralı veya test bu tablolar olmadan yazılamaz.

## User Story
As a backend developer
I want the initial Alembic migration for the 7 core tables (users, institutions, institution_members, talent_profiles, organizations, organization_members, skills)
So that Faz 1'in geri kalan tüm görevleri gerçek bir veritabanı şeması üzerine inşa edilebilsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given boş bir PostgreSQL 16 veritabanı, When `alembic upgrade head` çalıştırılır, Then 7 tablo (users, institutions, institution_members, talent_profiles, organizations, organization_members, skills) docs/DATABASE.md §2.1/§2.2'deki kolon/tip/default tanımlarıyla birebir, FK bağımlılık sırasına göre (users/institutions/organizations/skills önce, institution_members/organization_members/talent_profiles sonra) hatasız oluşturulur.
2. [Critical] Given her tablo, When kolonlar incelenir, Then tüm PK'lar `uuid` tipinde (UUIDv7 üretimi uygulama katmanında, bu görevde sadece kolon tipi tanımlanır), tüm `created_at`/`updated_at` `timestamptz NOT NULL DEFAULT now()`, `email`/`domain`/`slug`/`public_slug` kolonları `citext` tipindedir.
3. [Critical] Given docs/DATABASE.md'deki CHECK kısıtları (ör. `users.status`, `institutions.verification_level`, `skills.status<>'MERGED' OR merged_into_id IS NOT NULL`), When bu kurala aykırı bir INSERT denenir, Then PostgreSQL `IntegrityError` (CheckViolation) fırlatır ve işlem rollback olur.
4. [Critical] Given tüm UNIQUE kısıtları (ör. `institution_members(institution_id,user_id)`, `talent_profiles.user_id`, `skills.slug`), When aynı kombinasyon iki kez eklenir, Then `IntegrityError` (UniqueViolation) fırlatır.
5. [High] Given `alembic upgrade head` uygulanmış bir veritabanı, When `alembic downgrade -1` çalıştırılır, Then 7 tablo FK bağımlılığı ters sırada (önce institution_members/organization_members/talent_profiles, sonra users/institutions/organizations/skills) hatasız silinir.
6. [High] Given downgrade sonrası boş veritabanı, When `alembic upgrade head` tekrar çalıştırılır, Then hatasız tekrar oluşturulur (round-trip garantisi) — bu, migration dosyasının `upgrade()`/`downgrade()` fonksiyonlarının simetrik ve doğru yazıldığının kanıtıdır.
7. [Medium] Given `alembic upgrade head` zaten uygulanmış (head'de) bir veritabanı, When `alembic upgrade head` tekrar çalıştırılır, Then no-op olur, hata vermez, exit code 0 döner (Alembic'in kendi `alembic_version` takibi sayesinde).
8. [Medium] Given `skills` tablosundaki self-referencing FK'ler (`parent_id`, `merged_into_id`), When migration incelenir, Then bu FK'ler aynı `CREATE TABLE` içinde (nullable oldukları için) tanımlanmıştır, ayrı bir `ALTER TABLE` adımına gerek yoktur.

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme, kullanıcı girdisi, dosya yükleme/indirme, ödeme, kişisel veri (KVKK), çok kiracılı sınır, dış API çağrısı, arka plan işi, yeni bir HTTP ucu. Bu görev salt DDL/migration'dır — yeni bir HTTP ucu veya kullanıcı girdisi işleme eklemiyor. Tablolarda PII (email, password_hash, full_name) bulunsa da, bu kolonların varlığı ve KVKK anonimleştirme politikası (docs/DATABASE.md §"Anonimleştirme") zaten DOMAIN/DATABASE/SECURITY dokümanlarında onaylanmış tasarımın mekanik uygulanmasıdır — burada yeni bir güvenlik kararı alınmıyor. Gerçek threat-model, kullanıcı girdisi işleyen `YET-4` (auth uçları) ve yetkilendirme mantığını yazan `YET-2`'de yapılacak.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu görev bir CLI/DDL işlemidir (HTTP endpoint değil) — "dönen değer" Alembic/PostgreSQL'in exit code ve exception davranışıdır.

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — boş DB'de ilk `upgrade head` | Exit code 0 | 7 tablo, tüm kısıtlarla oluşur | Alembic log: her migration adımı başarıyla uygulandı | AC-1, AC-2 |
| 2 | Girdi geçersiz — CHECK/UNIQUE/NOT NULL ihlali (test verisiyle) | `IntegrityError` (CheckViolation/UniqueViolation/NotNullViolation) | Transaction rollback, hiçbir satır eklenmez | Exception + PostgreSQL hata mesajı | AC-3, AC-4 |
| 3 | Kaynak yok — var olmayan bir revision id'ye downgrade/upgrade | Alembic `CommandError` ("Can't locate revision") | Yok | Hata mesajı, exit code ≠0 | — (bu migration tek revizyon olduğu için pratikte tetiklenmez, ama Alembic'in genel davranışı budur) |
| 4 | Yetkisiz erişim | DB kullanıcısının `CREATE TABLE`/`CREATE EXTENSION` (citext için) yetkisi yoksa `InsufficientPrivilege` | Migration transaction'ı rollback olur, hiçbir DDL uygulanmaz | Hata mesajı, exit code ≠0 | — (bu ortamda docker-compose'daki DB kullanıcısı superuser, N/A ama production'da geçerli) |
| 5 | Dış bağımlılık hatası — Postgres'e bağlanılamıyor | `OperationalError`/connection refused | `alembic_version` güncellenmez | Bağlantı hatası mesajı | — |
| 6 | Zaman aşımı | N/A | — | — | Bu ilk migration'da tablolar boştan oluşturulduğu için pratik bir DDL kilidi/timeout senaryosu yok; ileride mevcut büyük bir tabloya kısıt eklerken (Faz 2+) geçerli olur |
| 7 | **Kısmi başarı** — 7 tablodan bazıları oluşup ortada hata çıkması | N/A (transaction sayesinde) | — | — | PostgreSQL DDL transactional'dır ve Alembic migration'ları varsayılan olarak tek transaction içinde çalışır — "kısmi başarı" durumu mimari olarak oluşamaz, ya hep ya hiç (all-or-nothing rollback) |
| 8 | **Hiçbir şey yapılamadı ama hata yok** — zaten head'deyken tekrar `upgrade head` | No-op, exit code 0 | Yok, `alembic_version` değişmez | "Already at head"e benzer sessiz başarı, ama bu GERÇEK bir başarıdır (hedef durum zaten sağlanmış) | AC-7 |

Kısmi başarı: Yukarıda gerekçelendirildiği gibi PostgreSQL DDL'in transactional olması sayesinde bu görevde imkansız — satır 7 N/A değil, "oluşamaz" olarak kanıtlanmış.
Hiçbir şey yapılamadı ama hata da yok: Satır 8'deki "no-op" durumu sessiz başarı DEĞİLDİR çünkü hedef durum (şema head'de) zaten sağlanmıştır — çağıranın gözlemleyebileceği şey (`alembic current` çıktısı) durumun doğruluğunu kanıtlar.
Boş sonuç ↔ hata ayrımı: Bu görevde "boş sonuç" kavramı yok (migration bir sorgu değil, DDL uygulaması) — N/A.

## Test Strategy
Unit: 20% — CHECK constraint davranışı testleri (her CHECK kuralına karşı bir "geçersiz değer reddedilir" testi, ORM seviyesinde mock'lanabilir kısımlar)
Integration: 70% — gerçek PostgreSQL 16'ya karşı (docker-compose'daki servis veya CI'daki Postgres) migration uygulama + `information_schema`/SQLAlchemy `inspect()` ile her tablonun/kolonun/FK'nin/UNIQUE'in/CHECK'in gerçekten var olduğunu doğrulayan testler
E2E: 10% — tam `upgrade head → downgrade -1 → upgrade head` zincirinin uçtan uca hatasız çalıştığını doğrulayan tek bir test

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (migration + model dosyaları için)
Performance Target: Yok (DDL işlemi, boş tablolarda performans kriteri anlamsız)
Memory: Yok
Diğer ölçülebilir kriterler:
- `alembic upgrade head` hatasız çalışır (exit code 0)
- `alembic downgrade -1` hatasız çalışır, tüm 7 tablo silinir
- `alembic upgrade head` tekrar hatasız çalışır (round-trip)
- pytest test seti her 7 tablonun tüm kolon/FK/CHECK/UNIQUE kısıtlarının var olduğunu doğrular

## Kapsam Dışı
- `skill_claims`, `engagements`, `evidence`, `evidence_skills`, `attestations`, `skill_signals`, `evaluations`, `verified_experiences`, `audit_events`, `outbox` tabloları — bunlar Faz 1'in sonraki maddelerinde (`YET-2` audit_events, `YET-5` outbox) veya Faz 2'de
- Seed verisi (skill taksonomisi) — `YET-10`'a ait
- Yetkilendirme mantığı (`can()`/`scoped_*()`) — `YET-2`'ye ait
- Auth endpoint'leri (kayıt/giriş) — `YET-4`'e ait
- Gerçek CRUD endpoint'leri (`GET /me`, institution/organization/skill uçları) — `YET-7/8/9/10/11`'e ait
- `pg_uuidv7` PostgreSQL eklentisine geçiş kararı — docs/DATABASE.md'de açık soru olarak işaretli, bu görevde uygulama katmanı (Python `uuid6`/`uuid7` paketi) tercih ediliyor (bkz. Assumptions)

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/` — yeni SQLAlchemy model dosyaları (users, institutions, institution_members, talent_profiles, organizations, organization_members, skills)
- `backend/alembic/versions/` — yeni migration dosyası (`alembic revision --autogenerate` ile üretilecek, CHECK constraint'ler elle gözden geçirilip eklenecek)
- `backend/tests/test_migration.py` — yeni test dosyası
- `backend/requirements.txt` — `uuid6` veya `uuid7` paketi eklenmesi gerekebilir (UUIDv7 üretimi için)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki görevde de teyit edildi): `projelerim/yetkin360` kendi git reposu, `projelerim/obss`'den bağımsız. Arama bu klasörle sınırlı kalmalı.

## Rollback Beklentisi
Bu görev henüz production/staging'e hiç deploy edilmemiş durumda (yeni migration, ilk kez yazılıyor) — CLAUDE.md'deki "uygulanmış migration'ı düzenleme/silme yasak, düzeltme yeni migration ile yapılır" kuralı bu migration'a HENÜZ uygulanmaz. Geliştirme ortamında migration dosyası serbestçe düzenlenip `downgrade`/`upgrade` ile yeniden denenebilir. Bu görev merge edilip staging/production'a uygulandıktan SONRA bu kural devreye girer — sonraki bir düzeltme ihtiyacı olursa yeni bir migration dosyası açılır, bu dosya asla elle değiştirilmez.

## Risks
- `pg_uuidv7` eklentisi yerine uygulama katmanında UUIDv7 üretme kararı bu görevde alınıyor (docs/DATABASE.md'de açık soru olarak işaretliydi) — ileride eklentiye geçilirse ek bir migration ve model değişikliği gerekir.
- Alembic'in `autogenerate` özelliği çoklu-kolon CHECK constraint'leri (ör. `skills` tablosundaki `status<>'MERGED' OR merged_into_id IS NOT NULL`) güvenilir şekilde tespit etmez — migration dosyası autogenerate sonrası elle gözden geçirilip eksik CHECK'ler manuel eklenmeli, aksi halde AC-3 sessizce başarısız olur.
- `citext` PostgreSQL extension'ının migration içinde `CREATE EXTENSION IF NOT EXISTS citext` ile etkinleştirilmesi gerekiyor — unutulursa tüm `citext` kolonları migration'da hata verir.

## Assumptions
- UUIDv7 üretimi uygulama katmanında (Python `uuid6`/`uuid7` paketiyle, SQLAlchemy modelinde `default=`) yapılacak, veritabanı server_default kullanılmayacak — bu, docs/DATABASE.md'deki açık soruya bu görev kapsamında verilen bir cevaptır, nihai karar değildir (Sonnet 5 low alt-ajanı tarafından önerildi, hackathon bağlamında en az sürtünmeli seçenek olduğu gerekçesiyle).
- Docker Compose'daki geliştirme veritabanı kullanıcısı superuser yetkisine sahip (CREATE EXTENSION için gerekli) — production'da bu farklı olabilir, o zaman "yetkisiz erişim" senaryosu (Davranış Sözleşmesi satır 4) gerçek bir risk haline gelir.

## Unknowns
- `pg_uuidv7` eklentisine ne zaman/nasıl geçileceği (docs/DATABASE.md'nin kendi açık sorusu, bu görevin kapsamı dışında bırakıldı).
- `skill_claim_history` tablosunun (docs/DATABASE.md'de "AÇIK SORU" olarak işaretli) bu migration'a dahil edilip edilmeyeceği — DATABASE.md'nin kendisi bunu netleştirmediği için bu migration'a DAHİL EDİLMEDİ (Kapsam Dışı listesinde zımnen yer alıyor, Jira YET-1 özeti de bu tabloyu adlandırmıyor).

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Backend geliştirici, doğrudan son kullanıcıya görünmez (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
2. Happy path → 7 tablo, FK sırasına göre, autogenerate + elle CHECK gözden geçirme (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. UUIDv7 üretim kararı → uygulama katmanında Python uuid6/uuid7 paketi (Sonnet 5 low alt-ajanı tarafından yanıtlandı: hackathon için en az sürtünmeli)
4. Downgrade davranışı → FK ters sırada DROP (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Idempotency → Alembic'in kendi alembic_version takibi ile no-op (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
6. CHECK ihlali davranışı → IntegrityError/CheckViolation (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Başarı ölçütü → upgrade+downgrade+upgrade round-trip + pytest kısıt doğrulama seti (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı → diğer tablolar, seed, yetkilendirme, auth, CRUD uçları, pg_uuidv7 kararı (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Test stratejisi → unit 20/integration 70/e2e 10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: DDL/şema görevi olduğu için integration ağırlıklı)
10. Rollback beklentisi → henüz production'a deploy edilmediği için serbest düzenleme, sonrasında CLAUDE.md kuralı devreye girer (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Self-referencing FK riski → aynı CREATE TABLE içinde, nullable olduğu için sorunsuz (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. docs/DATABASE.md'ye bağlılık → birebir, sapma varsa gerekçeyle not düşülür (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
13. Jira "membership" tekil isim vs. gerçek şema → (kullanıcı mesajından/doğrudan docs okuma) iki ayrı tablo: institution_members, organization_members
