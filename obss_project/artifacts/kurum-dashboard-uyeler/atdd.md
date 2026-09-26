---
task_slug: kurum-dashboard-uyeler
jira_id: YET-109
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 60
  integration: 30
  e2e: 10
affected_modules:
  - backend/app/api/institutions.py (DashboardResponse şemasına members alanı eklenecek, get_coordinator_dashboard_endpoint güncellenecek)
  - backend/app/services/engagement.py (get_coordinator_dashboard() içine üye sorgusu eklenecek — plan aşamasında bu dosyanın InstitutionMember import etmesinin mimari kurala uygunluğu doğrulanacak)
  - backend/tests/test_coordinator_dashboard.py (var olan dosya genişletilecek, yeni dosya değil)
---

# ATDD — kurum-dashboard-uyeler

## Jira Kaynağı
[YET-109 — [PLAN 3.5] Kurum dashboard ucu (bekleyen değerlendirmeler, üyeler)](https://kuyusuzyusuf123.atlassian.net/browse/YET-109)
Alt görevler: YET-133 (servis: üye listesi sorgusu), YET-134 (GET /institutions/{id}/dashboard ucu), YET-135 (yetkilendirme testi: çapraz-kurum erişim 404).
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.5. Sahip: @be2"

**Kapsam netliği (bu oturumda kullanıcıyla doğrulandı, YET-109'a Jira yorumu olarak da işlendi):**
`docs/API.md`'de `GET /institutions/{id}/dashboard` için tek bir kayıt var (satır 318). Bu uç
zaten var — YET-107/PLAN 3.3'te (takım arkadaşı Yusuf) yapıldı: `backend/app/api/institutions.py`,
`backend/app/services/engagement.py:get_coordinator_dashboard()`, yetkilendirmesi ve çapraz-kurum
404 testi (`test_coordinator_dashboard.py`) dahil. Mevcut response yalnız `institution_id`,
`summary` (`pending_approval`, `pending_evaluation` sayaçları), `pending_approval`/
`pending_evaluation` engagement listeleri döndürüyor — **üye listesi hiç yok**.

**Bu görevin TEK gerçek kalan kapsamı: mevcut uca/servise `members` alanı eklemek.** Yeni bir uç
AÇILMAYACAK. YET-134/YET-135 büyük ölçüde zaten tamamlanmış durumda (aynı uç, aynı yetkilendirme
testi) — bu ATDD yalnız `members` eklentisinin kabul kriterlerini tarif ediyor.

## Persona
Kurum koordinatörü veya kurum admin'i — kendi kurumundaki diğer ADMIN/COORDINATOR üyeleri görmek
(kimin yönetici yetkisi olduğunu bilmek, iletişim kurmak, gerekirse rol/üyelik kararları almak) için.

## Hedef (Neden)
Koordinatör dashboard'u zaten "durum takibi" sağlıyor; "üyeler" eksik olduğu için koordinatör
kendi kurumundaki diğer yöneticileri görmek için ayrı bir yola (DB sorgusu, e-posta vb.) başvurmak
zorunda kalıyor. Bu bilgi tek ekranda toplanmalı.

## User Story
As a kurum koordinatörü/admin'i
I want kendi kurumumdaki diğer ADMIN/COORDINATOR üyeleri dashboard'da görmek
So that kimin yönetici yetkisi olduğunu ayrı bir sorgu yapmadan bilebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kendi kurumuna ait koordinatör/admin, When `GET /institutions/{id}/dashboard`
   çağrılır, Then response'a `members: list[{user_id, email, role, joined_at}]` alanı eklenir,
   kurumdaki TÜM `InstitutionMember` (ADMIN+COORDINATOR) kayıtlarını içerir.
2. [Medium] Given kurumda (teorik olarak) hiç üye yoksa, When istek gönderilir, Then
   `members: []` döner (hata değil, `200`).
3. [Critical] **(AC-S1, threat-model)** Given iki farklı kurumun (A ve B) her ikisinde de üye
   varken, When A'nın koordinatörü `GET /institutions/{A_id}/dashboard` çağırır, Then `members`
   listesinde SADECE A'nın üyeleri bulunur, B'nin hiçbir üyesi (email dahil) sızmaz.
4. [High] (YET-135, zaten mevcut — bu görev tarafından DEĞİŞTİRİLMİYOR, tekrar test edilmiyor)
   Given çapraz-kurum veya yetkisiz erişim, When istek gönderilir, Then `404` döner (mevcut
   davranış, `test_coordinator_dashboard.py`'de zaten test edili).

## Davranış Sözleşmesi (yalnız bu görevin eklediği kısım için)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (üyeler var) | `200` + `members` dolu | Yok (salt-okunur) | Üye listesi | AC-1 |
| 2 | Kurumda üye yok (teorik) | `200` + `members: []` | Yok | Boş liste | AC-2 |
| 3 | Cross-tenant sızıntı riski | `members` yalnız istenen `institution_id`'ye ait satırları içerir | Yok | — | AC-S1 |

Uygulanmayan satırlar ve neden silindiği:
- **Girdi geçersiz/eksik** — N/A: `institution_id` path parametresi framework seviyesinde (UUID
  tipi) zaten doğrulanıyor, bu görev yeni bir girdi almıyor.
- **Kaynak yok/yetkisiz erişim** — N/A: bu görev DEĞİŞTİRMİYOR, mevcut davranış (404) aynen
  korunuyor (AC-4'te referans verildi, tekrar test edilmiyor).
- **Dış bağımlılık hatası/zaman aşımı** — N/A: aynı DB session içinde ek bir SELECT, yeni ağ
  çağrısı veya dış servis bağımlılığı yok.
- **Kısmi başarı** — N/A: tek sorgu + response birleştirme, ara durum mimari olarak mümkün değil.
- **Hiçbir şey yapılamadı ama hata yok** — N/A: yukarıdakiyle aynı gerekçe.

## Güvenlik Kabul Kriterleri (threat-model, STRIDE-lite)

Varlık/sınır: `InstitutionMember` + `User.email` verisi, kurum → coordinator güven sınırı (zaten
var olan bir sınır, ama YENİ bir veri alanı bu sınırdan geçiyor).

STRIDE-lite:
- **Spoofing:** Atlandı — yeni bir kimlik kanıtlama mekanizması yok, mevcut auth kullanılıyor.
- **Tampering:** Atlandı — bu bir `GET`, yeni bir client-supplied girdi yok.
- **Repudiation:** Atlandı — salt-okunur bir görüntüleme, state değişikliği yok, mevcut projede
  `GET /institutions/{id}/engagements` gibi benzer okuma uçları da audit edilmiyor (tutarlı).
- **Info disclosure:** **Asıl risk burada.** Projede `scoped_institution_members()` gibi hazır bir
  yetkilendirme yardımcı fonksiyonu YOK (`backend/app/services/authorization.py` kontrol edildi —
  yalnız `scoped_institutions`, `scoped_engagements` vb. var). Yani `code-copilot` bu sorguyu
  SIFIRDAN yazacak — `institution_id` filtresini unutmak (ör. `select(InstitutionMember)` filtresiz
  çalıştırmak) gerçek bir risk. → **AC-S1**.
- **DoS:** Sayfalama yok (bilinçli kabul edilen risk — aşağıda).
- **Elevation:** Atlandı — yeni bir erişim yolu/endpoint yok, mevcut endpoint'in zaten doğruladığı
  rol kontrolü (`principal.kind` COORDINATOR/INST_ADMIN) değişmeden kullanılıyor.

**Kabul edilen risk (bilinçli, kapsam dışı):** Üye listesinde sayfalama yok. Gerekçe: bir kurumun
ADMIN/COORDINATOR sayısı doğası gereği küçük (yönetici rolü, öğrenci/talent değil) — MVP'de
gereksiz karmaşıklık. İleride ihtiyaç doğarsa ayrı bir PLAN maddesi.

**authz-test skill'i:** Bu görevde ayrıca çağrılmadı — AC-S1 zaten `test-copilot`/`verify`
aşamasında gerçek çalışan sisteme karşı iki-kurum senaryosuyla test edilecek (PLAN 3.4'teki
kararla tutarlı: canlı IDOR probe'ları `verify` aşamasında).

## Test Strategy
Unit: 60% — üye sorgusunun `institution_id` filtresi, response birleştirme mantığı
Integration: 30% — endpoint + DB (gerçek `InstitutionMember`/`User` join)
E2E: 10% — `pytest tests/authorization -q` üzerinden mevcut çapraz-kurum senaryosunun hâlâ
geçtiğinin doğrulanması

Yetkilendirme etkilenen bir uç değiştiği için CLAUDE.md kuralı gereği `pytest tests/authorization -q`
tamamı zorunlu.

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: yok (saf backend, frontend bileşeni bu görevin kapsamında değil)
Diğer ölçülebilir kriterler: mevcut `test_coordinator_dashboard.py` testlerinin hiçbiri kırılmamalı
(bkz. Risks).

## Kapsam Dışı
- Yeni bir uç açmak — mevcut `GET /institutions/{id}/dashboard` genişletiliyor.
- `TalentProfile` (öğrenci) listesi eklemek — "üyeler" burada yalnız ADMIN/COORDINATOR anlamına
  geliyor, öğrenci listesi kavramsal olarak farklı, ayrı bir PLAN maddesi olabilir.
- Üye davet/silme/rol değiştirme — bunlar zaten `POST /institutions/{id}/members` ile ayrı bir uç,
  bu görev salt-okunur bir liste ekliyor.
- Sayfalama — bilinçli kabul edilen risk (yukarıda).
- YET-134/YET-135'in "yeniden yapılması" — bunlar zaten tamamlanmış, bu görev sadece üzerine ekliyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/institutions.py` — `DashboardMemberItem` (yeni Pydantic response şeması,
  `DashboardEngagementItem`'ın yanına, aynı desen) + `DashboardResponse`'a `members` alanı +
  `get_coordinator_dashboard_endpoint` güncellemesi.
- `backend/app/services/engagement.py` — `get_coordinator_dashboard()` içine üye sorgusu.
  **Açık soru (plan aşamasında doğrulanacak):** bu dosyanın `InstitutionMember` modelini import
  etmesi mimari kurala ("modüller birbirinin iç dosyasını import etmez") aykırı mı? Model importu
  genelde paylaşılan `models/` katmanından sayıldığı için sorun çıkmaması bekleniyor, ama plan
  aşamasında gerçek dosya okunarak teyit edilecek.
- `backend/tests/test_coordinator_dashboard.py` — genişletilecek (yeni dosya değil).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki PLAN 3.4 görevinde): `git rev-parse --show-toplevel` proje klasörüyle
(`/Users/elifsarahan/Desktop/yetkin360`) aynı. Arama bu klasörle sınırlı tutulacak.

## Rollback Beklentisi
Salt-okunur bir ekleme (yeni bir SELECT + response alanı), transaction/rollback riski yok —
mevcut endpoint'in transaction davranışı değişmiyor.

## Risks
- **Mevcut testler kırılabilir:** `test_coordinator_dashboard.py`'nin happy-path testi
  `response.json() == {...tam sözlük...}` şeklinde TAM eşleşme yapıyorsa, yeni `members` alanı bu
  testi kırar. Plan aşamasında gerçek test dosyası okunarak doğrulanacak; kırılıyorsa aynı
  commit'te (ayrı bir görev açmadan) güncellenecek.
- `engagement.py`'nin `InstitutionMember` importu mimari kurala uygunluk açısından plan aşamasında
  teyit edilecek (yukarıda not düşüldü).
- Sayfalama yok — kabul edilen risk (yukarıda).

## Assumptions
- `joined_at` alanı `InstitutionMember.created_at` (TimestampMixin) — ayrı bir "üyelik tarihi"
  alanı yok, `created_at` bu amaçla yeniden kullanılıyor.
- Email adresinin response'ta görünmesi bilinçli bir karar (institution-içi görünürlük, log
  kuralından farklı) — kullanıcı onayı bekleniyor (Hard Stop'ta).

## Unknowns
- `engagement.py`'ye üye sorgusu eklemenin mi, yoksa `institution.py` diye ayrı bir servis
  fonksiyonunun mu daha doğru olduğu — Sonnet alt-ajanı `engagement.py`'yi önerdi (mimari
  tutarlılık, tek fonksiyonda toplama), ama plan aşamasında gerçek dosya yapısına bakılarak
  kesinleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1-11: Sonnet 5 low alt-ajanı tarafından yanıtlandı (ATDD skill kuralı gereği kullanıcı bu
netleştirme sorularıyla durdurulmadı). Tam cevap metni bu oturumun agent-message kaydında;
özet doğrudan yukarıdaki bölümlere işlendi. Kapsam netliği (hangi işin zaten yapılmış olduğu)
kullanıcıyla doğrudan konuşularak netleştirildi (bu, alt-ajana sorulmadı — zaten kullanıcı
mesajından netti).
