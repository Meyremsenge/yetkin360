---
task_slug: yet-8-institution-koordinator-ogrenci-bagi
jira_id: YET-8
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 65
  e2e: 15
affected_modules:
  - backend/app/services/institution.py (yeni)
  - backend/app/api/institutions.py (yeni)
  - backend/app/services/authorization.py (mevcut — scoped_institutions()/can() genişletmesi)
  - backend/app/models/identity.py (mevcut — Institution/InstitutionMember zaten var, değişmez)
  - backend/app/models/institution_link_request.py (yeni — InstitutionLinkRequest modeli)
  - backend/alembic/versions/ (yeni migration — institution_link_requests tablosu, kullanıcı onayıyla)
  - docs/API.md (yeni bölüm — Institutions, kod yazımından önce)
  - docs/DATABASE.md (yeni tablo dokümantasyonu — institution_link_requests)
---

# ATDD — yet-8-institution-koordinator-ogrenci-bagi

## Jira Kaynağı
[YET-8 — [PLAN 1.8] Institution + koordinatör rolü + öğrenci bağı](https://kuyusuzyusuf123.atlassian.net/browse/YET-8)

User Story (Jira'dan birebir): "As a university I want to register as an institution and assign a coordinator role to a staff member So that my students' engagements have someone with the authority to confirm they're real"

Açıklama (Jira'dan birebir): "PLAN.md Faz 1, madde 1.8. Owner: backend-1. Institution entity, koordinatör rolü ve öğrenci-kurum bağı. docs/DOMAIN.md'deki ilişki kurallarına uyulur."

Bağımlılık doğrulaması: YET-1 (ilk migration) ve YET-2 (yetkilendirme çekirdeği) ikisi de Tamamlandı, YET-8 bloke değil.

**Kod keşfinden doğrulanan durum:** `Institution` (id, name, domain, verification_level T1-T4, status) ve `InstitutionMember` (institution_id, user_id, role ADMIN|COORDINATOR) modelleri `backend/app/models/identity.py`'de **zaten var** (YET-1 migration'ında). Bu görev sadece servis+API katmanını ekliyor, şema değişmiyor.

**Belgelenmemiş sözleşme (önemli, kullanıcıya bildirilmeli):** `docs/API.md`'de bu görevin ihtiyaç duyduğu uçlar (kurum oluşturma, koordinatör davet, öğrenci-bağ onayı) hiç tanımlanmamış — sadece Faz 3'e ait `/institutions/{id}/dashboard`, `/engagements`, `/reminders` var. En yakın emsal `docs/API.md`'deki `/organizations` deseni (`POST /organizations` → 201/T1, `POST /organizations/{id}/members` → davet, `POST /organizations/{id}/verify-domain` → T1→T2) — `docs/DOMAIN.md` zaten `InstitutionMember`'ı "Organization ile simetrik" olarak tanımlıyor. Bu görev kapsamında `docs/API.md`'ye **kod yazımından önce** Organization deseniyle simetrik yeni bir "Institutions" bölümü eklenmeli (proje "sözleşme önce" ilkesi).

## Persona
Üniversite temsilcisi/personeli — kurumu platforma kaydeden ve koordinatör atayan kişi (Jira User Story'sinden birebir).

## Hedef (Neden)
Öğrencilerin engagement'larının gerçekliğini onaylayacak yetkili bir kişinin (koordinatör) kurumla ilişkilendirilmesi — `beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirinde kurumsal doğrulama katmanının temelini atmak.

## User Story
As a university representative
I want to register my institution and assign a coordinator role to a staff member
So that my students' engagements have someone with the authority to confirm they're real

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir kullanıcı, When `POST /institutions` (`name`, `domain?`) çağrılır, Then `201` döner (`verification_level: T1`), çağıran kullanıcı otomatik olarak `InstitutionMember(role=ADMIN)` olur.
2. [Critical] Given bir `Institution`'ın `ADMIN`'i, When `POST /institutions/{id}/members` (`email`, `role`) çağrılır, Then `201` döner ve davet edilen kullanıcı belirtilen rolle (`ADMIN`|`COORDINATOR`) üye olarak eklenir/davet edilir.
3. [Critical] Given bir `TalentProfile` sahibi öğrenci, When kendi profilini bir kuruma bağlamak için `POST /institutions/{id}/link-requests` çağırırsa, Then yeni bir `institution_link_requests` kaydı `PENDING` durumda oluşur — `TalentProfile.institution_id` henüz set EDİLMEZ.
3b. [Critical] Given `PENDING` durumda bir `institution_link_requests` kaydı, When ilgili kurumun bir `COORDINATOR`'ı veya `ADMIN`'i `POST /institutions/{id}/link-requests/{request_id}/approve` çağırırsa, Then kayıt `APPROVED` olur VE `TalentProfile.institution_id` bu kuruma set edilir (D10 böylece açık istek + açık onay ile karşılanır — bkz. plan.md, migration onaylandı).
4. [Critical/AC-S1] Given bir `Institution`'ın `COORDINATOR`'ı (ADMIN değil), When bu kullanıcı `POST /institutions/{id}/members` çağırırsa, Then `404` döner (403 değil — CLAUDE.md kuralı), hiçbir üyelik oluşturulmaz.
5. [Critical/AC-S2] Given Kurum A'nın bir `COORDINATOR`'ı, When Kurum B'ye ait bir öğrenci-bağ onay isteğini (institution_id'yi tahmin ederek/deneyerek) onaylamaya çalışırsa, Then `404` döner, istek onaylanmaz, Kurum B'nin öğrenci-bağ isteği durumu değişmez.
6. [High] Given aynı `domain` değerine sahip bir kurum zaten varsa, When ikinci bir `POST /institutions` aynı domain ile çağrılırsa, Then `409 DOMAIN_TAKEN` döner.
7. [High] Given var olmayan bir `institution_id`, When `POST /institutions/{id}/members` çağrılırsa, Then `404` döner.
8. [Medium] Given bir öğrenci-bağ isteği zaten `PENDING` durumundayken, When aynı öğrenci aynı kuruma tekrar bağlanma isteği atarsa, Then `409 Conflict` döner (sessiz "başarılı" YASAK — yeni bir PENDING kaydı oluşmaz).

## Threat Model
Çağrıldı. STRIDE-lite uygulandı:
- **Elevation of Privilege (çekirdek risk):** `ADMIN`-only eylemlerin (üye davet etme) sunucuda, sadece `InstitutionMember.role` DB'den kontrol edilerek uygulanması → AC-S1 (AC-4).
- **Tampering / Information Disclosure (BOLA, çekirdek risk):** İstemciden gelen `institution_id`'ye güvenilmeyip her istekte gerçek üyelik DB'den doğrulanması, kapsam dışı kuruma erişimde `404` (varlık sızdırmadan) dönmesi → AC-S2 (AC-5).
- **Repudiation, Spoofing, DoS:** Kapsam dışı bırakıldı — Repudiation zaten `audit_events` (YET-2) altyapısıyla genel olarak ele alınıyor, bu görev yeni bir log noktası eklemiyor; Spoofing (kimlik doğrulama sağlamlığı) YET-4'ün sorumluluğunda kabul edildi; DoS/rate-limit bu görevde ele alınmıyor (davet spam'i düşük öncelik, `docs/SECURITY.md`'nin genel rate-limit kapsamına bırakıldı).

AC-S kriterleri yukarıdaki Acceptance Criteria listesine AC-4 (AC-S1) ve AC-5 (AC-S2) olarak gömüldü — ayrı bölüm açılmadı.

**`authz-test` skill'i notu:** Bu görev doğrudan bir tenant-izolasyon/BOLA senaryosu (Kurum A vs Kurum B) ürettiği için `test-copilot` adımında `authz-test` skill'i çağrılmalı — en az iki farklı kurum (Kurum A/B) ile karşılaştırmalı test kalıbı (YET-3'ün zaten kurduğu Org A/B fixture desenine benzer şekilde, Institution A/B fixture'ları eklenerek).

## Agentic Değerlendirme Kriterleri
Tetikleyici yok — klasik backend endpoint görevi, LLM agent davranışı değiştirmiyor.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — kurum oluşturma + koordinatör davet + öğrenci-bağ onayı | `201` (kurum) → `201` (davet) → onay sonrası `200`/`202` (bağ etkinleşti) | Kurum/üyelik/bağ kaydı DB'ye yazılır | "Kurum oluşturuldu", "Davet gönderildi", "Öğrenci kuruma bağlandı" | AC-1, AC-2, AC-3 |
| 2 | Girdi geçersiz/eksik (`name` boş, geçersiz `domain` formatı) | `422` alan bazlı hata | Yok | Alan altı hata mesajı | — |
| 3 | Kaynak yok (var olmayan `institution_id`'ye üye davet) | `404` | Yok | "Bulunamadı" | AC-7 |
| 4 | Yetkisiz erişim (COORDINATOR üye davet etmeye çalışır / başka kurumun COORDINATOR'ı bağ isteğini onaylar) | `404` (403 değil) | Yok | "Bulunamadı" (varlık sızmaz) | AC-4, AC-5 |
| 5 | Dış bağımlılık hatası (davet e-postası gönderimi başarısız) | Üyelik kaydı yine de `201` ile commit edilir | E-posta gönderimi `outbox` tablosuna yazılır, worker retry eder — CLAUDE.md: ağ çağrısı asla açık transaction içinde yapılmaz | "Davet gönderildi" (arka planda retry) | AC-2 |
| 6 | Zaman aşımı | N/A | — | — | Bu görevde senkron dış çağrı yok — e-posta `outbox` üzerinden asenkron, senkron timeout riski yok |
| 7 | **Kısmi başarı** — kurum oluşturuldu, davet e-postası gönderilemedi | Kurum + üyelik kaydı kalıcı, `201` döner | `outbox`'a "gönderilemedi" event'i yazılır | "Davet gönderildi" (kullanıcı email gecikmesini fark etmez, worker arka planda dener) | AC-2 |
| 8 | **Hiçbir şey yapılamadı ama hata yok** — öğrenci-bağ isteği zaten `PENDING`'ken tekrar istek | `409 Conflict` | Yeni PENDING kaydı OLUŞMAZ | "Zaten bekleyen bir isteğiniz var" | AC-8 |

Kısmi başarı: Satır 7'de detaylandırıldı — kurum/üyelik verisi kalıcı, sadece bildirim yan etkisi (e-posta) gecikebilir, bu durum kullanıcıya "başarısız" olarak yansımaz çünkü asıl işlem (kayıt) başarılıdır.
Hiçbir şey yapılamadı ama hata da yok: Yasak — tekrar eden bağ isteği `409` ile açıkça reddedilir, sessiz "200 ama hiçbir şey olmadı" YOK (satır 8).
Boş sonuç ↔ hata ayrımı: Kapsam dışı kurum (`404`) ile gerçekten var olmayan kurum (`404`) aynı sonucu üretir — bilinçli tasarım (AC-S2, 404 sızıntı önleme, YET-2'nin `get_scoped_or_404()` deseniyle tutarlı).

## Test Strategy
Unit: 20% — domain validasyonu (name/domain format), rol kontrolü mantığı.
Integration: 65% — gerçek Postgres'e karşı `can()`/`scoped_institutions()` genişletmesi, Institution A/B tenant izolasyonu (AC-S2), ADMIN/COORDINATOR yetki ayrımı (AC-S1).
E2E: 15% — kurum oluştur → koordinatör davet et → öğrenci bağ isteği → onay zincirinin uçtan uca senaryosu (gerçek HTTP, TestClient).

`test-copilot`'a extra_instructions: `authz-test` kalıbı uygulanmalı — en az iki farklı kurum (Institution A/B) ile karşılaştırmalı test, "boş liste/404 PASS'e çevrilmez" ilkesi (YET-2/YET-3'ten devralınan authz-test prensibi).

## Benchmark / Başarı Ölçütü
Coverage Target: %85.
Performance Target: Yok.
Memory: Yok.
Diğer ölçülebilir kriterler: Her yeni endpoint (`POST /institutions`, `POST /institutions/{id}/members`, öğrenci-bağ-istek/onay uçları) için en az 1 pozitif + 1 negatif yetkilendirme testi (CLAUDE.md kuralı) — toplam en az 8 yetkilendirme testi beklenir.

## Kapsam Dışı
- T2-T4 doğrulama seviyeleri (domain doğrulaması dahil) — bu görev sadece T1 kurum oluşturmayı kapsar; domain doğrulama (T1→T2) `Organization`'daki gibi ayrı bir görev olabilir, YET-8'in Jira açıklamasında buna dair bir madde yok.
- Faz 3 uçları (`/institutions/{id}/dashboard`, `/engagements`, `/reminders`) — zaten `docs/API.md`'de ayrı, tamamlanmamış.
- `TalentProfile`'ın `GET`/`PATCH` uçları — YET-7'nin işi.
- Koordinatör onayının UI/frontend tarafı — bu görev backend-only.
- AI/matching/gamification — CLAUDE.md'nin MVP dışı listesi.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/identity.py` — `Institution`/`InstitutionMember` (mevcut, değişmez).
- `backend/app/services/institution.py` (yeni) — kurum oluşturma, üye davet, öğrenci-bağ isteği/onay iş mantığı.
- `backend/app/api/institutions.py` (yeni) — HTTP router.
- `backend/app/services/authorization.py` (mevcut) — `scoped_institutions()` gibi yeni bir `scoped_*()` fonksiyonu ve `can()`'a Institution-ilişkili action'lar eklenmesi gerekecek (YET-2'nin kendi mantığı değişmez, sadece genişler).
- `docs/API.md` — yeni "Institutions" bölümü (kod yazımından önce, Organization deseniyle simetrik).
- Öğrenci-bağ isteği için yeni bir tablo gerekebilir (ör. `institution_link_requests` — `TalentProfile.institution_id` doğrudan set edilmiyorsa PENDING durumu bir yerde tutulmalı) — bu bir **migration** anlamına gelir, kullanıcı onayı gerektirir (CLAUDE.md).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı: `projelerim/yetkin360` kendi git reposu. `backend/.venv/` altında devasa bir site-packages ağacı var — Grep/Glob/Bash **her zaman** `backend/app`, `backend/tests`, `docs/`, `PLAN.md` ile sınırlanmalı, `.venv` içine asla girilmemeli (YET-3'te bu hatadan dönüldü, tekrarlanmamalı).

## Rollback Beklentisi
`Institution`/`InstitutionMember` append-only listesinde DEĞİL — ama kanıta dayalı platformda iz kaybı istenmediği için fiziksel silme yapılmaz, durum alanı (`status`/`role`) güncellenerek "iptal/deaktive et" şeklinde geri alınır. Yeni migration (öğrenci-bağ isteği tablosu) geliştirme ortamında serbestçe düzenlenebilir, henüz prod'a gitmedi.

## Risks
- **Kabul edilen risk (Repudiation/Spoofing/DoS kapsam dışı):** Yukarıda Threat Model bölümünde gerekçelendirildi — kimlik doğrulama sağlamlığı YET-4'e, davet spam'i rate-limit'i genel `docs/SECURITY.md` kapsamına bırakıldı.
- Öğrenci-bağ isteği için yeni bir tablo/migration gerekip gerekmediği netleşmedi (bkz. Unknowns) — bu, `plan` adımında gerçek şemaya bakılarak netleşmeli, migration gerekiyorsa kullanıcı onayı şart (CLAUDE.md).
- `docs/API.md`'nin bu görevde güncellenmesi gerektiği (yeni bölüm) — CLAUDE.md'nin "3+ dosyayı etkileyen refactor" veya "dokümantasyon" onay eşiğine girmeyebilir ama açık kaynak repo olduğu için tutarlılık riski var, `plan` adımında dosya listesine eklenmeli.

## Assumptions
- Öğrenci-bağ akışının `POST /organizations` deseniyle simetrik olduğu varsayıldı (Sonnet 5 low alt-ajanı tarafından önerildi) — bu, Jira açıklamasında veya `docs/API.md`'de birebir doğrulanmamış bir çıkarımdır, `plan` adımında `docs/DOMAIN.md`/`docs/STATE_MACHINE.md` tekrar kontrol edilmeli.
- Davet e-postası gönderiminin `outbox` deseni üzerinden asenkron yapılacağı varsayıldı (CLAUDE.md'nin genel kuralından, bu görev için özel olarak Jira'da belirtilmemiş).

## Unknowns
- Öğrenci-bağ "PENDING" durumu nerede tutulacak — yeni bir tablo mu (`institution_link_requests`), yoksa `TalentProfile`'a `pending_institution_id` gibi bir alan mı eklenecek? `plan` adımında gerçek şema kararı verilmeli, migration gerekiyorsa kullanıcıya sorulmalı.
- T1→T2 domain doğrulamasının Institution için ayrı bir Jira görevi olup olmadığı bilinmiyor (Organization'da `YET-9` benzeri bir görev vardı) — YET-9'un içeriği bu ATDD'de kontrol edilmedi, kapsam dışı varsayıldı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Üniversite temsilcisi/personeli (Sonnet 5 low alt-ajanı tarafından yanıtlandı: Jira User Story'den)
2. Ana hedef → Öğrenci engagement'larını onaylayacak koordinatörün kurumla ilişkilendirilmesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path → kurum oluştur → koordinatör davet et → öğrenci-bağ isteği PENDING → koordinatör onayı (Sonnet 5 low alt-ajanı tarafından yanıtlandı, /organizations deseninden esinlenerek)
4. Edge case'ler → aynı domain ikinci kurum (409), COORDINATOR'ın ADMIN-only eylemi denemesi (404) (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Davranış sözleşmesi tablosu → yukarıya işlendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
6. Başarı ölçütü → coverage ≥85% + her endpoint için pozitif/negatif yetkilendirme testi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Kapsam dışı → T2-T4, Faz 3 uçları, TalentProfile GET/PATCH (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Bağımlılıklar → identity.py (mevcut), yeni institution.py/institutions.py, authorization.py genişletmesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Güvenlik kısıtı → BOLA/tenant-leakage çekirdek risk (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
10. Rollback → fiziksel silme yok, durum alanı ile deaktivasyon (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Kabul kriteri sahibi → otomatik CI + owner PR review (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Test stratejisi → unit 20/integration 65/e2e 15 (Sonnet 5 low alt-ajanı tarafından yanıtlandı, HTTP endpoint'leri olduğu için YET-2'den biraz daha e2e ağırlıklı)
13. API.md güncellemesi → Evet, kod yazımından önce Organization deseniyle simetrik yeni bölüm eklenmeli (Sonnet 5 low alt-ajanı tarafından yanıtlandı: "sözleşme önce" ilkesi)
14. Threat-model AC-S1/AC-S2 → STRIDE-lite analizinden (threat-model skill tarafından üretildi, bu oturumda)
