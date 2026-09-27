---
task_slug: calismalar-gercek-backend-baglama
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit:
    backend: 70
    frontend: 80
  integration:
    backend: 30
    frontend: 20
  e2e: 0
affected_modules:
  - backend/app/api/engagements.py
  - backend/app/services/engagement.py
  - backend/tests/authorization/test_engagement_authorization.py
  - frontend/lib/api/engagements.ts
  - frontend/lib/api/engagements.test.ts
---

# ATDD — calismalar-gercek-backend-baglama

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (kullanıcı doğrudan istedi). İlgili geçmiş
Jira görevleri: YET-73/95/96/97 (PLAN 2.11, mock ile tamamlanmıştı).

## Kaynak Belge
[ENTEGRASYON_NOTU.md](../yet-73-95-96-97-engagement-frontend-mock/ENTEGRASYON_NOTU.md) —
bu görevin TAM olarak neyi tamamlayacağını önceden belgelemiş: `GET
/engagements` (liste) ve `GET /engagements/{id}` (detay) backend'de yok,
frontend `USE_MOCK_LIST`/`USE_MOCK_DETAIL = true` ile localStorage
simülasyonu kullanıyor. Bu ATDD o notun "Backend GET uçları eklendiğinde
yapılacaklar" bölümünü uygular.

## Persona
TALENT (kendi çalışmalarını görür), ORG_MEMBER/ORG_ADMIN (kendi
organizasyonlarının çalışmalarını görür), COORDINATOR/INST_ADMIN (kendi
kurumlarının çalışmalarını görür) — hepsi AYNI iki ucu (liste+detay) kullanır,
`scoped_engagements()` tenant izolasyonunu satır bazında zaten yapıyor.

## Hedef (Neden)
`/calismalar` sayfası şu an gerçek veri değil, localStorage mock'u
gösteriyor — kalıcı değil, sekmeler arası paylaşılmıyor (F5 dışında),
gerçek beyan→kanıt→tanıklık zincirinin bir parçası değil. Bu görev bunu
gerçek, kalıcı, yetkilendirilmiş backend verisine bağlıyor.

## User Story
As a TALENT/ORG_MEMBER/ORG_ADMIN/COORDINATOR/INST_ADMIN
I want kendi kapsamımdaki çalışmaları (engagement) gerçek backend'den
listelemek ve detayını görmek
So that mock/geçici veri yerine kalıcı, doğru veriyle çalışabilirim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir TALENT, When `GET /engagements` çağırır, Then kendi `talent_id`'sine ait TÜM engagement'lar `{items: [{id, title, kind, status, organization_name, version, updated_at}]}` şeklinde döner.
2. [Critical] Given kimliği doğrulanmış bir ORG_MEMBER/ORG_ADMIN, When `GET /engagements` çağırır, Then sadece kendi `organization_id`'lerine ait engagement'lar döner (başka organizasyonların engagement'ları görünmez).
3. [Critical] Given kimliği doğrulanmış bir COORDINATOR/INST_ADMIN, When `GET /engagements` çağırır, Then sadece kendi `institution_id`'lerine ait engagement'lar döner.
4. [Critical] Given kapsamdaki bir engagement ID'si, When `GET /engagements/{id}` çağırır, Then `tasks[]` ve `deliverables[]` dahil tam detay döner (AC-1'deki alanlar + `talent_id, organization_id, institution_id, reason, created_at, tasks, deliverables`).
5. [Critical] Given kapsam DIŞI bir engagement ID'si (başka tenant'a ait), When `GET /engagements/{id}` çağırır, Then `404` döner (403 değil — CLAUDE.md kuralı, kaynağın var/yok olduğu sızdırılmaz).
6. [Critical] Given var OLMAYAN bir engagement ID'si, When `GET /engagements/{id}` çağırır, Then AYNI `404` döner (var/yok ayırt edilemez).
7. [High] Given hiç engagement'ı olmayan bir kullanıcı, When `GET /engagements` çağırır, Then `{items: []}` döner (boş liste, hata değil).
8. [High] Given `limit`/`offset` query parametreleri, When `GET /engagements?limit=10&offset=0` çağırır, Then offset/limit sayfalama uygulanır (admin ekranlarıyla tutarlı kalıp).
9. [Medium] Given frontend `USE_MOCK_LIST`/`USE_MOCK_DETAIL` kaldırılmış, When `/calismalar` sayfası açılır, Then gerçek `GET /engagements`/`GET /engagements/{id}` çağrılır, mock store kodu (seedEngagements/loadStore/saveStore/findInStore) tamamen silinmiş olur.

## Threat Model
Çağrıldı — tetikleyiciler: çok kiracılı (multi-tenant) sınır (TALENT/ORG/
INST arasında engagement izolasyonu), yeni HTTP ucu (2 yeni GET ucu).
STRIDE-lite: **Elevation/Info disclosure** öne çıktı — kapsam dışı bir
engagement'a ID tahmin ederek erişim denemesi (IDOR) en somut risk.
AC-S1/AC-S2 aşağıda eklendi.

**AC-S1 [Critical]:** Given TALENT A, When TALENT B'nin engagement ID'sini
doğrudan `GET /engagements/{B'nin_id}` ile dener, Then `404` döner (`403`
değil) ve response body'de B'ye ait HİÇBİR alan (title, organization_name
vb.) sızmaz.

**AC-S2 [Critical]:** Given bir ORG_MEMBER, When kendi organizasyonu
DIŞINDAKİ bir engagement'ın ID'sini `GET /engagements/{id}` ile dener,
Then `404` döner — var olan ve olmayan ID için yanıt AYIRT EDİLEMEZ (aynı
kod, aynı gövde şekli).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path liste (TALENT) | `200 {"items":[{"id":"...","title":"...","kind":"INTERNSHIP","status":"ACTIVE","organization_name":"Acme A.Ş.","version":1,"updated_at":"2026-09-27T10:00:00Z"}]}` | Yok (salt okunur) | Çalışmalar listesi | AC-1 |
| 2 | Happy path detay | `200 {..., "talent_id":"...","organization_id":"...","institution_id":null,"reason":null,"created_at":"...","tasks":[{"id":"...","title":"...","status":"DONE"}],"deliverables":[{"id":"...","title":"...","submitted_at":"..."}]}` | Yok | Detay sayfası | AC-4 |
| 3 | Kaynak yok / kapsam dışı | `404 {"code":"NOT_FOUND","message":"Engagement bulunamadı.","request_id":null}` | Yok | "Çalışma bulunamadı" satır-içi uyarı (mevcut `calismalar/[id]/page.tsx` kalıbı) | AC-5, AC-6, AC-S1, AC-S2 |
| 4 | Yetkisiz erişim (kimlik doğrulanmamış) | `401 {"code":"UNAUTHORIZED","message":"Kimlik doğrulama gerekli.","request_id":null}` | Yok | `/giris`'e yönlendirme (mevcut oturum mantığı) | — |
| 5 | Dış bağımlılık hatası (500/network) | `500` veya `NetworkError` | Yok | Genel hata bandı, retry | — |
| 6 | Zaman aşımı | `NetworkError("timeout")` | Yok | "İstek zaman aşımına uğradı" | — |
| 7 | **Kısmi başarı** | — silindi | Bu görev salt-okunur (GET), yazma işlemi yok — kısmi başarı senaryosu oluşmaz | — | — |
| 8 | **Hiçbir şey yapılamadı ama hata yok** | Boş liste → `200 {"items":[]}` | Yok | "Henüz bir çalışmanız yok" boş-durum mesajı | AC-7 |

Boş sonuç ↔ hata ayrımı: `200 {"items":[]}` = "bu kapsamda engagement yok"
(AC-7); `404` = "bu ID kapsamda değil veya yok" (AC-5/AC-6) — ikisi asla
karışmaz, farklı HTTP kodları.

## Test Strategy
**Backend** — Unit 70%: `list_engagements()`/`get_engagement_detail()` servis
fonksiyonları (scoped_engagements + organization JOIN + tasks/deliverables
sorgusu). Integration 30%: `tests/authorization/test_engagement_authorization.py`'ye
TALENT/ORG_MEMBER/ORG_ADMIN/COORDINATOR/INST_ADMIN × liste/detay × kapsam-içi/
kapsam-dışı matrisi (mevcut kalıp).
**Frontend** — Unit 80%: `engagements.ts`'in gerçek `apiFetch("/engagements")`
çağrısı yaptığını doğrulayan testler (mock store testleri SİLİNİR). Integration
20%: `calismalar/page.test.tsx`/`calismalar/[id]/page.test.tsx` gerçek response
şekliyle render testi (zaten `lib/api/engagements` mock'lanarak test ediliyor,
sadece mock verinin şekli gerçek API şemasına güncellenir).
E2E: 0% — proje genelinde yok.

## Benchmark / Başarı Ölçütü
Coverage Target: %85 (yetkilendirme-kritik kod, `.claude/rules/security.md`
"her yeni endpoint = aynı commit'te yetkilendirme testi" kuralı gereği daha
yüksek).
Performance Target: yok.
Görsel/UI kriteri: Yok — frontend'in JSX'i değişmiyor, sadece veri kaynağı
(`lib/api/engagements.ts`) değişiyor, `frontend-pipeline` tetikleyicisi yok.
Diğer: N+1 sorgu YASAK — `organization_name` JOIN ile tek sorguda gelmeli.

## Kapsam Dışı
- `GET /me`'ye `principal.kind`/`role` eklenmesi — ENTEGRASYON_NOTU'nun
  kendi kararı, bu görevde de geçerli kalır.
- `availableTransitions()`'ın role-bazlı filtrelenmesi — aynı gerekçe,
  gerçek yetki zaten `POST /transitions`'da sunucuda uygulanıyor.
- Cursor tabanlı sayfalama — MVP'de veri hacmi küçük, offset/limit yeterli.
- `confidential=true` engagement'lar için özel gizleme mantığı — `scoped_engagements()`
  zaten sadece yetkili tarafları döndürüyor, ek bir gizleme katmanı bu
  görevde eklenmiyor (bkz. Unknowns).
- Tasks/deliverables için yazma/güncelleme uçları — bu görev sadece OKUMA
  (liste+detay) ekliyor, mevcut `POST /tasks`/`POST /deliverables` zaten var.
- `EvidenceRecord` ile Deliverable arasındaki ilişki — mevcut modelde ayrı,
  bu görev sadece Deliverable'ın kendi alanlarını (`id, title, submitted_at`)
  dönüyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/engagements.py` — 2 yeni GET endpoint.
- `backend/app/services/engagement.py` — `list_engagements()`/`get_engagement_detail()` servis fonksiyonları.
- `backend/tests/authorization/test_engagement_authorization.py` — yetkilendirme matrisi genişletilir.
- `frontend/lib/api/engagements.ts` — mock store kodu SİLİNİR, `USE_MOCK_LIST`/`USE_MOCK_DETAIL` kaldırılır.
- `frontend/lib/api/engagements.test.ts` — mock-store testleri gerçek apiFetch mock'una güncellenir.
- Backend response şeması gereği: `Organization.name` JOIN edilecek.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — sonraki adımlarda arama proje klasörüyle (`yetkin360/`)
sınırlanmalı.

## Rollback Beklentisi
Salt-okunur (GET) uçlar — DB yazması yok, rollback kavramı uygulanmıyor.
Frontend geçişi bir görsel/davranış regresyonu yaratırsa `git revert` yeterli.

## Risks
- Frontend'in `EngagementDetail` tipi (`organization_name`, `tasks`,
  `deliverables`) backend response'uyla TAM eşleşmezse (alan adı farkı),
  sessiz bir tip uyumsuzluğu oluşabilir — `test-copilot`/`code-copilot`
  arasındaki kopukluk riskini azaltmak için Davranış Sözleşmesi'ndeki JSON
  örnekleri BİREBİR kullanılmalı.
- Mevcut `lib/api/engagements.test.ts`'in mock-state-machine testleri
  (`transitionEngagement`'ın mock dallanması) bu görevde SİLİNMİYOR —
  `transitionEngagement` zaten gerçek uca gidiyordu (mock sadece
  list/detail'de), o testler değişmeden kalabilir.

## Assumptions
- Coverage %85 ve test oranları (backend 70/30, frontend 80/20) — proje
  genel konvansiyonundan ve "yetkilendirme-kritik" sınıflandırmasından
  varsayıldı, kullanıcı onayı bekliyor.
- Offset/limit sayfalama (cursor değil) — MVP kapsamı gerekçesiyle varsayıldı.

## Unknowns
- `confidential=true` engagement'ların listede/detayda özel bir işaretle
  (ör. bir rozet) gösterilip gösterilmeyeceği netleşmedi — bu görevde alan
  response'a eklenmiyor, ileride ayrı bir görev olabilir.

## Sorular ve Cevaplar (ham kayıt)
1. Rol → Tek uç, `scoped_engagements()` üzerinden tüm rol tipleri. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
2. Ana hedef → Mock'u kalıcı gerçek veriye bağlamak. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
3. Happy path → Kullanıcının verdiği akış yeterli. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
4. Edge case'ler → Boş liste, kapsam-dışı 404, var-olmayan-ID 404 (aynı davranış). (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
5. Sayfalama → Offset/limit. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — varsayım, onay bekliyor.)
6. organization_name → JOIN, N+1 yasak. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
7. confidential → MVP'de gizleme/alan eklenmiyor, Unknowns'a yazıldı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
8. Kapsam dışı → /me principal.kind, role-bazlı availableTransitions, cursor, confidential gizleme, tasks/deliverables yazma uçları. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
9. Mock temizliği → Evet, tamamen silinir (ENTEGRASYON_NOTU'nun kendi talimatı). (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
10. Test stratejisi → Backend 70/30/0, frontend 80/20/0. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — onay bekliyor.)
11. Kabul kriteri sahibi → Otomatik test + red-team + kullanıcının canlı denemesi. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
12. Risk/varsayım → ENTEGRASYON_NOTU'nun /me kararı bu görevde de geçerli. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
