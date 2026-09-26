---
task_slug: seed-verisi-ogrenci-kurum-engagement
jira_id: YET-115
saga_task_id: null
threat_model: not-applicable
priority: medium
coverage_target: 80
performance_target: "<30s (tek python -m scripts.seed çalıştırması)"
memory_target: null
test_strategy:
  unit: 80
  integration: 20
  e2e: 0
affected_modules:
  - backend/scripts/seed.py
  - backend/app/services/auth.py (register_user — okuma amaçlı, değişiklik beklenmiyor)
  - backend/app/services/institution.py (create_institution — okuma amaçlı)
  - backend/app/services/organization.py (create_organization — okuma amaçlı)
  - backend/app/services/engagement.py (create_engagement/transition_engagement — okuma amaçlı)
  - backend/app/services/evaluation.py (create_evaluation — okuma amaçlı)
  - backend/app/services/attestation.py (create_attestation — okuma amaçlı)
---

# ATDD — seed-verisi-ogrenci-kurum-engagement

## Jira Kaynağı
[YET-115 — [PLAN 3.11] Seed verisi: 20 öğrenci, 5 kurum, 15 tamamlanmış engagement](https://kuyusuzyusuf123.atlassian.net/browse/YET-115)
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.11.\nSahip: @be1"
Alt görevler: YET-152 ("scripts/seed.py: 20 öğrenci + 5 kurum + 15 engagement üretimi"), YET-153 ("Seed verisiyle smoke test doğrulaması" — bu görevin KAPSAMI DIŞINDA, ayrı bir Jira maddesi).
Tip: Görev · Öncelik: Medium · Durum: Yapılacaklar
Saga: bu oturumda Saga MCP sunucusuna bağlanılamadı (araç listesinde yok) — `saga_task_id` kaydedilemedi.

## Persona
Backend geliştirici (@be1) — yerel geliştirme ortamında (Docker Compose + PostgreSQL) manuel olarak `python -m scripts.seed` çalıştırır. CI/deploy pipeline'ının parçası değil, bir dev-ortam aracıdır.

## Hedef (Neden)
Koordinatör dashboard, kurum dashboard, profil sayfası gibi ekranların gerçekçi veriyle manuel test edilebilmesi ve YET-153'ün (seed verisiyle smoke test) üzerine inşa edebileceği tutarlı bir temel veri kümesi oluşturmak. Şu an bu ekranlar (bu oturumda da doğrulandığı gibi, `koordinator-dashboard-frontend` görevinde) gerçek bir COORDINATOR hesabıyla test edilemiyor çünkü DB'de öğrenci/kurum/engagement verisi yok.

## User Story
As a backend geliştirici (@be1)
I want tek bir komutla (`python -m scripts.seed`) 20 öğrenci, 5 kurum, 15 tamamlanmış (VERIFIED) engagement içeren tutarlı bir veri kümesi oluşturmak
So that dashboard/profil ekranlarını gerçek veriyle manuel test edebileyim ve YET-153 smoke test'i bu veriye güvenebilsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given temiz bir veritabanı (migration'lar uygulanmış, veri yok), When `python -m scripts.seed` çalıştırılır, Then DB'de tam olarak 20 `TalentProfile`, 5 `Institution`, en az 5 `Organization` (her engagement bir organization'a bağlı olmalı, FK constraint), 15 `Engagement` (hepsi `status='VERIFIED'`) oluşur.
2. [Critical] Given script ikinci kez çalıştırılır (idempotency), When `python -m scripts.seed` tekrar çalıştırılır, Then DB'deki kayıt sayıları DEĞİŞMEZ (20/5/15 aynı kalır) — mevcut `seed_skills()` kalıbıyla tutarlı (email/slug üzerinden var-mı kontrolü).
3. [Critical] Given VERIFIED bir engagement, When bu engagement'a bağlı kayıtlar incelenir, Then en az bir `Attestation` ve bir `VerifiedExperience` kaydı da append-only tablolara **gerçek servis fonksiyonları üzerinden** (`create_evaluation`, `create_attestation` — doğrudan `INSERT ... status='VERIFIED'` DEĞİL) yazılmış olmalı — append-only tabloya (CLAUDE.md §Veri) elle INSERT ile "sahte" VERIFIED durumu üretmek audit_events/outbox yan etkilerini atlar, bu yasak.
4. [High] Given script bir DB hatasıyla (ör. bağlantı kopması) ortasında kesilir, When script yeniden çalıştırılır, Then DB'de kısmi/tutarsız veri KALMAZ — tüm seed işlemi tek bir transaction'a alınır, hata durumunda `session.rollback()` ile tamamen geri alınır.
5. [High] Given `settings.environment == "production"`, When script çalıştırılmaya çalışılır, Then script hiçbir kayıt oluşturmadan hata verip `exit code 1` ile çıkar (üretimde yanlışlıkla 20 sahte öğrenci oluşturma riskine karşı — bkz. Risks, YET-47 ile ilişkili ama bu görevin YENİ yazdığı fonksiyon için de baştan gerekli).
6. [Medium] Given DB bağlantısı hiç kurulamıyorsa (Docker Compose ayakta değil), When script çalıştırılır, Then anlamlı bir hata mesajıyla (`OperationalError` yakalanıp yeniden fırlatılır) `exit code 1` ile çıkar, stack trace yerine okunabilir bir mesaj gösterilir.
7. [Medium] Given 15 engagement dağıtılırken, When 20 öğrenci arasında dağıtım yapılır, Then dağıtım eşit olmak ZORUNDA değildir (gerçekçi veri: bazı öğrencinin 0, bazısının 2 engagement'ı olabilir) — ama her engagement geçerli bir `talent_id`/`organization_id`/`institution_id` FK'sine sahip olmalı.

## Threat Model
Tetikleyici yok — değerlendirilen tetikleyiciler: kimlik doğrulama/yetkilendirme (bu script yeni bir authz kararı eklemiyor, mevcut servis fonksiyonlarını olduğu gibi çağırıyor), kullanıcı girdisi (CLI script'i parametre almıyor, sabit sayılar kodda), dosya yükleme/indirme (evidence mock, gerçek MinIO I/O yok), ödeme (yok), kişisel veri/KVKK (üretilen veri tamamen SAHTE/sentetik test verisi, gerçek bir kişiye ait değil), çok-kiracılı sınır (yeni bir HTTP ucu yok, tenant-scoping değişmiyor), dış API çağrısı (yok, outbox'a yazılıp gönderilmeyecek), arka plan işi (script tek seferlik, worker değil), yeni HTTP ucu (yok) — hiçbiri uymadı çünkü bu bir CLI dev-araçı, mevcut servis fonksiyonlarını tüketiyor, yeni bir güvenlik yüzeyi açmıyor.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (temiz DB, ilk çalıştırma) | `exit code 0` | 20 TalentProfile + 5 Institution + ≥5 Organization + 15 Engagement (VERIFIED) + ilgili Evaluation/Attestation/VerifiedExperience/SkillSignal/audit_events/outbox kayıtları | Konsolda "20 öğrenci, 5 kurum, 15 engagement oluşturuldu" özeti | AC-1 |
| 2 | Idempotency (ikinci çalıştırma) | `exit code 0` | Yeni kayıt oluşturulmaz | Konsolda "Zaten mevcut, atlanıyor" mesajı, sayılar değişmez | AC-2 |
| 3 | DB bağlantı hatası ortasında kesilme | `exit code 1` | Tam rollback — DB'de 0 yeni kayıt | Konsolda hata mesajı + "hiçbir değişiklik uygulanmadı" | AC-4 |
| 4 | Production ortamında çalıştırma denemesi | `exit code 1`, hiçbir DB işlemi başlamadan | Yok | Konsolda "Bu script production'da çalıştırılamaz" mesajı | AC-5 |
| 5 | DB'ye hiç bağlanılamıyor | `exit code 1` | Yok | Konsolda "Veritabanına bağlanılamadı" mesajı | AC-6 |

Kısmi başarı: Uygulanmaz olarak KABUL EDİLMEDİ, ayrı bir AC'ye (AC-4) bağlandı — tüm seed işlemi tek transaction'a alınır, "10 öğrenci oluştu 5'i oluşmadı" durumu asla kalıcı olmaz (ya hep ya hiç).
Hiçbir şey yapılamadı ama hata da yok: İkinci çalıştırmada (AC-2) tam olarak budur — 0 yeni kayıt oluşur ama bu bir hata değil, idempotency'nin doğru çalıştığının kanıtıdır; script yine `exit code 0` ile başarı bildirir çünkü DB zaten istenen durumdadır (mevcut `seed_skills()`'in "X inserted, Y already exist" mesaj kalıbıyla tutarlı).
Boş sonuç ↔ hata ayrımı: "Zaten seed'lenmiş" (AC-2, exit 0) ile "seed edilemedi" (AC-3/4/5/6, exit 1) farklı exit code'larla ve farklı konsol mesajlarıyla ayrılır — ikisi asla aynı çıktıyı paylaşmaz.

## Test Strategy
Unit: 80% — her `seed_X()` fonksiyonu (`seed_talents()`, `seed_institutions()`, `seed_organizations()`, `seed_engagements()` gibi, tam isimlendirme `plan` adımında netleşecek) için: doğru sayı üretildi mi, tekrar çağrılınca sayı artmıyor mu (idempotency), FK/CHECK ihlali yok mu, ENVIRONMENT=production'da hiç çalışmıyor mu.
Integration: 20% — gerçek PostgreSQL'e karşı (testcontainers veya proje testlerinin zaten kullandığı gerçek-DB deseni) tam script çalıştırması, DB'de gerçekten 20/5/15 sayılarının oluştuğunun doğrulanması.
E2E: 0% — bu görevin kapsamında değil, YET-153'e devredildi.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: <30 saniye (tek `python -m scripts.seed` çalıştırması, yerel Docker Compose PostgreSQL'e karşı)
Memory: —
Görsel/UI kriteri: Yok — bu bir backend CLI script'i, UI/frontend içermiyor.
Diğer ölçülebilir kriterler: İkinci çalıştırmada DB'deki satır sayıları birebir aynı kalmalı (idempotency, otomatik test edilebilir).

## Kapsam Dışı
- Frontend seed'i (yok, bu tamamen backend/DB katmanı).
- Gerçek dosya yükleme (evidence/attestation belgesi MinIO'ya gerçekten yüklenmez — mock/placeholder path kullanılır, CLAUDE.md kapsam kuralı "MVP dışı özellik yazma" ve gerçek I/O bu görevin amacı değil).
- Gerçek e-posta gönderimi (outbox tablosuna yazılır ama worker tarafından gönderilmez — CLAUDE.md kuralı: "ağ çağrısı açık transaction içinde yapılmaz", bu script zaten bir transaction içinde çalışıyor).
- YET-153 (seed verisiyle smoke test doğrulaması) — ayrı bir Jira maddesi, bu görevin ürettiği veriyi TÜKETECEK ama bu görevde yazılmayacak.
- Script'e komut satırı parametresi (sayı özelleştirme, `--students=30` gibi) eklenmesi — MVP'de sabit sayılar (20/5/15) yeterli, YAGNI.
- Mevcut `seed_skills()` fonksiyonuna ENVIRONMENT koruması eklenmesi (bu YET-47'nin kapsamı, bu görev sadece YENİ yazılan fonksiyonlara bu korumayı ekler).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/scripts/seed.py` — yeni `seed_students_institutions_engagements()` (veya benzeri, `plan` adımında kesinleşecek) fonksiyon(lar)ı eklenecek, mevcut `seed_skills()` ve `if __name__ == "__main__":` bloğu genişletilecek.
- Kullanılacak (değiştirilmeyecek) servis fonksiyonları: `register_user` (auth.py), `create_institution`/`invite_member` (institution.py), `create_organization`/`invite_org_member` (organization.py), `create_engagement`/`transition_engagement` (engagement.py), `create_evaluation` (evaluation.py), `create_attestation` (attestation.py).
- Migration: YOK bekleniyor (mevcut şema zaten tüm gerekli tabloları içeriyor) — `plan` adımında teyit edilmeli.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmış: git reposunun kökü proje klasörüyle aynı (`C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\yetkin360`), önceki görevlerde teyit edildi.

## Rollback Beklentisi
Script hata verirse tüm transaction rollback edilir (AC-4) — DB'de hiçbir kısmi kayıt kalmaz. Idempotent olduğu için script güvenle tekrar çalıştırılabilir.

## Risks
- ENVIRONMENT koruması olmadan bu script yanlışlıkla production'a karşı çalıştırılırsa 20 sahte kullanıcı/kurum üretebilir — AC-5 ile bu risk kapatıldı, ama mevcut `seed_skills()`'te AYNI koruma yok (YET-47'nin kapsamı, bu görevde dokunulmayacak — Kapsam Dışı'nda not edildi).
- "Tamamlanmış" (VERIFIED) durumuna gerçek servis zinciriyle (transition_engagement + create_evaluation + create_attestation) ulaşmanın tam adım sırası bu ATDD'de netleşmedi — `plan` adımında kod okunarak kesinleştirilmeli (bkz. Unknowns).
- `saga_task_id` bu oturumda oluşturulamadı (Saga MCP bağlı değil).

## Assumptions
- "15 tamamlanmış engagement" = `status='VERIFIED'` (zincirin son durumu: beyan → kanıt → tanıklık → doğrulanmış deneyim) varsayıldı — kullanıcı onayı alınmadı ama proje genelinde "tamamlanmış"ın başka bir anlamı yok (EVALUATED durumu ara adım, DISPUTED/RESOLVED istisna senaryoları).
- Test kullanıcıları için sabit/dummy bir şifre (`.env.example`'a placeholder olarak değil, kod içinde sabit bir test-only string, ör. `"SeedTest123!"`) kullanılacağı varsayıldı — CLAUDE.md ".env okunmaz, sır sabitleri koda yazılmaz" kuralı GERÇEK sırlar için geçerli, bu sentetik test kullanıcıları için sabit bir şifre bir "sır" değildir (zaten dev-ortamda, herkese açık repo'da, gerçek hiçbir hesaba karşılık gelmiyor) — yine de `plan` adımında teyit edilmeli.

## Unknowns
- VERIFIED durumuna ulaşmak için gerekli tam servis çağrı sırası (`create_engagement` → `transition_engagement(ACTIVE)` → ? → `create_evaluation` → ? → `create_attestation` → VERIFIED) `plan` adımında `backend/app/services/evaluation.py` ve `attestation.py`'nin tam içeriği okunarak netleştirilmeli — bu ATDD'de sadece fonksiyonların VAR OLDUĞU doğrulandı, hangi fonksiyonun status'u hangi ara duruma taşıdığı doğrulanmadı.
- Institution/Organization/Engagement arasındaki tam FK ilişkisi (bir engagement'ın hem institution_id hem organization_id'ye mi sahip olduğu, yoksa institution_id'nin nullable olup olmadığı) `plan` adımında modelden teyit edilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → geliştirici, yerel manuel çalıştırma (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CI/deploy pipeline'ı değil, dev-ortam aracı).
2. Ana hedef/neden → manuel test + YET-153 smoke test'ini beslemek (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
3. Happy path (dağılım) → 20/5/15, eşit olmayan gerçekçi dağılım, her engagement bir organization'a bağlı (Sonnet 5 low alt-ajanı tarafından yanıtlandı: FK constraint gereği organization'lar da seed edilmeli).
4. Edge case'ler → DB bağlantı hatası (exit 1) / idempotency (exit 0, sayı değişmez) (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
5. Davranış sözleşmesi tablosu → dolduruldu, "yetkisiz erişim"/"zaman aşımı" satırları silindi (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLI script, HTTP endpoint değil; script saniyeler sürer).
6. Başarı ölçütü → <30s, DB'de tam 20/5/15 (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → frontend seed/gerçek dosya-email/YET-153/CLI parametreleri/seed_skills() düzeltmesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı + orkestratör tarafından YET-47 ayrımı netleştirildi).
8. Bağımlılıklar → register_user/create_institution/create_organization/create_engagement/transition_engagement/create_evaluation/create_attestation (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör tarafından kod okumasıyla fonksiyon isimleri teyit edildi).
9. Performans/güvenlik kısıtı → ENVIRONMENT kontrolü bu görevin kapsamında (Sonnet 5 low alt-ajanı tarafından yanıtlandı: YENİ yazılan fonksiyon baştan bu korumayla yazılmalı, YET-47 sadece seed_skills()'i geriye dönük düzeltir).
10. Rollback → tek transaction, tam rollback (Sonnet 5 low alt-ajanı tarafından yanıtlandı: kısmi veri idempotency'yi bozar).
11. Kabul kriteri sahibi → @be1 manuel + unit/idempotency testi (Sonnet 5 low alt-ajanı tarafından yanıtlandı: gerçek e2e/smoke YET-153'e devredildi).
12. Test stratejisi oranı → 80/20/0 (Sonnet 5 low alt-ajanı tarafından yanıtlandı: e2e YET-153'e devredildi).
13. Threat-model tetikleyici → yok (orkestratör tarafından değerlendirildi: CLI dev-araçı, sentetik veri, yeni HTTP ucu/authz dalı yok).
