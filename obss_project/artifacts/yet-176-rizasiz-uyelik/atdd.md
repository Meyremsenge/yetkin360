---
task_slug: yet-176-rizasiz-uyelik
jira_id: YET-176
saga_task_id: null
priority: high
threat_model: done
coverage_target: n/a (yalnız test; üretim kodu değişmiyor)
performance_target: null
memory_target: null
test_strategy:
  unit: 0
  integration: 100
  e2e: 0
affected_modules:
  - backend/tests/authorization/test_nonconsensual_membership.py (yeni)
---

# ATDD — yet-176-rizasiz-uyelik

## Jira Kaynağı
YET-176 — GUV-02: Rızasız üyelik ataması, kurbanın kind değişip talent işlevleri kapanıyor (High, Yapılacaklar).
Açıklama (özet): Herhangi bir kullanıcı kurum/org açıp rızası olmadan başka kullanıcıyı üye yapabiliyor; kurbanın kind'ı değişip talent işlevlerini kaybediyor. "Kısmen kapandı: YET-165'te 500, e-posta numaralandırma, L-01. Açık kalan: kurbanın kind değişmesi, AUTHZ-01'e bağımlı."

## Sonda bulgusu (2026-10-01, gerçek API, tests/authorization/test_nonconsensual_membership_probe.py)
| Yüzey | Durum | Kanıt |
|---|---|---|
| Kurban rızasız org ADMIN + kurum ADMIN yapıldıktan sonra GET /engagements, GET /engagements/{id}, POST deliverables, GET evidence download-url, GET verified-experiences, PATCH /talents/me | **KAPALI** (YET-187) | hepsi 200/201 |
| Herhangi biri POST /institutions, /organizations ile kurum/org açıp ADMIN olur | **AÇIK**, karar: kapsam dışı | 201 |
| ADMIN e-posta ile anında üye yapar (onay yok, bildirim yok); kurumda mevcut üyenin rolü sessizce ezilir | **AÇIK** | 201, ADMIN→COORDINATOR ezme 201 |
| Son-admin koruması (kurum self-demote) | **AÇIK** (YET-236 L-01; git'te YET-165 commit'i yok) | self-demote 201 |
| Org: bilinmeyen e-posta | **AÇIK, 500** (ValueError yakalanmıyor) — YET-180 | TestClient istisna fırlattı |
| Kurum: bilinmeyen e-posta 422 vs bilinen 201 (numaralandırma) | **AÇIK** | 422 "User not found" |
| Kurbanın üyelikten çıkma ucu | **YOK** (DELETE yok) | grep: iki router'da yalnız POST/GET |
| Üyelik status/PENDING filtresi | Kolon yok → kapsam dışı (K1 (b), davet/kabul Faz 5) | |
| Bildirim yok | YET-209 (outbox worker) sonrası | |

## Persona
Hedef kullanıcı (talent) — kendisi bilmeden başka birinin kurumuna/org'una üye yapılmış.

## Hedef
Rızasız üyelik atamasının kurbanın talent işlevlerini ve verisini bozmadığını, saldırgana da kurban verisi açmadığını regresyon testiyle sabitlemek. Kod değişmez.

## User Story
As a talent, I want my own engagements, evidence, and verified experiences to stay fully usable even if someone adds me to their org/institution, so that a non-consensual membership cannot lock me out.

## Acceptance Criteria
1. [Critical] Given kurban rızasız org ADMIN + kurum ADMIN yapıldı (gerçek POST /…/members ile), When GET /engagements, Then 200 ve kurbanın kendi engagement'ı listede (başka org'unki).
2. [Critical] Given aynı durum, When GET /engagements/{id}, Then 200.
3. [Critical] Given aynı durum + ACTIVE engagement, When POST /engagements/{id}/deliverables, Then 201 ve DB'de deliverable var (submitted_by = kurban).
4. [Critical] Given aynı durum, When GET /evidence/{id}/download-url (CLEAN), Then 200.
5. [Critical] Given aynı durum, When GET /talents/me/verified-experiences/, Then 200 ve kayıt listede; GET /me talent_profile dolu ve organizations/institutions saldırganınkini içerir.
6. [High] Given aynı durum, When PATCH /talents/me, Then 200 ve DB'de değişti.
7. [High] Given saldırgan kendi org/kurumuna kurbanı ekledi, When saldırgan kurbanın engagement'ına (GET/POST deliverables/transitions), kanıtına (download-url), verified-experience'ına erişmeye çalışır, Then 404 (403 değil); kayıt DB'de var; reddedilen yazma sonrası DB yeniden okununca değişmemiş.
8. [High] Given kurban yalnız kurumda ADMIN yapıldı (talent + inst ADMIN), When engagement geçişi dener, Then K3(a): INST_ADMIN geçiş yapamaz (davranış değişmez) ama kendi talent işlevleri sürer.
9. [Medium] Given kurbanın başka org'da zaten üyeliği var, When rızasız üyelik eklenir, Then önceki org erişimi bozulmaz (kapsam birleşimi).

## Davranış Sözleşmesi
| # | Durum | Dönen | Yan etki | Kullanıcı görür | AC |
|---|---|---|---|---|---|
| 1 | Happy: kurban talent işlevlerini çağırır | 200/201 | deliverable kaydı | normal | AC-1..6 |
| 2 | Saldırgan kurban kaynağına erişir | 404 | yok | bulunamadı | AC-7 |
| 3 | Reddedilen yazma | 404 | DB değişmez | — | AC-7 |
Satır silindi: girdi geçersiz/dış bağımlılık/zaman aşımı — bu iş yeni uç eklemiyor; mevcut uçların sözleşmesi ilgili testlerde. Kısmi başarı / sessiz başarı: yok; deliverable POST'u tek transaction, test DB'den doğrular.
Boş sonuç ↔ hata: GET /engagements 200 + boş liste "kurban işlevini kaybetti" olurdu; test listede kurbanın kaydını assert ederek ayırır.

## Threat Model (AC-S)
Saldırgan = kurum/org açabilen herhangi bir kullanıcı.
- AC-S1 (kapsam yükseltme): Üye yapılan kurban üzerinden saldırgan kurban verisini görmemeli → AC-7.
- AC-S2 (self-dealing maskesi): Kurban hem talent hem org ADMIN iken kendi engagement'ında org/koordinatör bayrakları False kalır; kendi engagement'ını attest etmeye çalışırsa 409 SELF_ATTESTATION_FORBIDDEN (mevcut sözleşme; YET-187 testleri kapsıyor, tekrar yazılmaz).
- AC-S3 (yetkisiz = 404): saldırganın kurban kaynaklarına her erişimi 404.
- Kapsam dışı tehdit: davet/kabul yokluğu (K1 (b), Faz 5), bildirim yokluğu (YET-209), spam üyelik / çıkış ucu yokluğu (aşağıda).

## Çıkış ucu kararı (araştırma)
Kullanıcı: "gerekliyse sonra ekle, değilse ekleme; önce araştır." Sonuç: **eklenmeyecek.** (1) beyan→kanıt→tanıklık→doğrulanmış deneyim zinciri çıkış ucu olmadan çalışıyor (CLAUDE.md kapsam testi); (2) kurbanın hiçbir talent işlevi kapanmıyor (AC-1..6), saldırgana veri açılmıyor (AC-7); tek etki /me listesinde yabancı org/kurum adı görünmesi (rahatsızlık, yetki değil); (3) asıl çözüm davet+kabul akışı (Faz 5), çıkış ucu geçici yama olur; (4) yeni endpoint ayrı yetkilendirme testi ve sahiplik kararı (son-admin ile etkileşim) gerektirir. AÇIK TAKİP'e yazılır.

## Test Strategy
Integration 100%: gerçek Postgres, TestClient, gerçek POST /…/members çağrıları (fixture ile üyelik kurmak yerine saldırganın API'si).
Mutasyon: eski sürüm c748101 (YET-187'den önce) ile yeni testler koşulacak; kırmızı olması beklenir.

## Benchmark
Yeni test dosyası yeşil; backend 962/0/5 → artar, authz 474/4 → artar; ruff temiz; mypy yalnız 4 eski rowcount.

## Kapsam Dışı
Üretim kodu, migration, davet/kabul, PENDING, çıkış ucu, bildirim, org 500 (YET-180), numaralandırma, son-admin (YET-236), rol ezme.

## Proje Ortamı Kısıtı
Git kökü proje klasörü; arama backend/ ile sınırlı tutuldu.

## Rollback
Yalnız yeni test dosyası eklenir; geri alma = dosyayı silmek.

## Risks
- Eski kodda (c748101) fixture/model uyumsuzluğu mutasyon koşusunu bozabilir.

## Assumptions
- K1 (b) ve K3 (a) kararları geçerli (kullanıcı mesajı).
- Org/kurum ucunda e-posta numaralandırma ve 500 düzeltmesi bu görevde YAPILMAYACAK (kullanıcı kararı: yalnız regresyon testi). Bu iki yüzeyin regresyon testi de bu yüzden YAZILMAYACAK (mevcut davranış hatalı, test kırmızı olurdu ve gevşek assert yasak).

## Unknowns
- YET-165'in kodu başka bir branch'te olabilir (git --all grep'te yok).

## Sorular ve Cevaplar (ham kayıt)
Sonnet 5 alt-ajanı çağrılmadı: kategoriler kullanıcı mesajından (kapsam, bilinçli karar, YET-187 bilgisi, süreç dersleri) ve sondadan somut cevaplı; kapsam ve çıkış ucu soruları kullanıcıya soruldu: kapsam → "yalnız regresyon testi"; çıkış ucu → "gerekliyse ekle, değilse ekleme; önce araştır" (araştırıldı, eklenmeyecek).
