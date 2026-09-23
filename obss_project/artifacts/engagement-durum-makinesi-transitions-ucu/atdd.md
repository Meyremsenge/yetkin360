---
task_slug: engagement-durum-makinesi-transitions-ucu
jira_id: null
saga_task_id: null
threat_model: done
priority: critical
coverage_target: 90
performance_target: "<200ms"
memory_target: null
test_strategy:
  unit: 70
  integration: 25
  e2e: 5
affected_modules:
  - backend/app/api/engagements.py (yeni route: POST /{id}/transitions)
  - backend/app/services/engagement.py (yeni: transition_engagement())
  - backend/app/services/authorization.py (yeni: geçiş-özel yetki kontrolü — yetkilendirme mantığı değişikliği, açık onay gerekli)
  - backend/tests/authorization/test_matrix.py (yeni geçiş-özel testler)
---

# ATDD — engagement-durum-makinesi-transitions-ucu

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (PLAN.md 2.2). Saga MCP bu ortamda mevcut değil — `saga_task_id: null`.

## Persona
Tek uç, çoklu aktör: **TALENT** veya **ORG:MEMBER** (T1), **INST:COORD** (T2, T3), **ORG:ADMIN** veya **INST:COORD** (T6). Aktör kimliği geçiş anında `can_transition()`/transition tablosuyla çözülür — ayrı role-özel uç yok.
(Sonnet 5 low alt-ajanı tarafından yanıtlandı)

## Hedef (Neden)
DRAFT bir engagement PENDING_APPROVAL'a geçmeden ACTIVE olamaz, ACTIVE olmadan sonraki adımlar (Deliverable/Evaluation, PLAN 2.4+) üretilemez. Bu uç, PLAN 2.1'de oluşturulan statik `status=DRAFT` kaydını canlı bir sürece sokan tek mekanizma — bu uç olmadan zincir çalışmaz.

## User Story
As a talent, organizasyon üyesi, koordinatör veya organizasyon admini
I want kendi yetkim dahilindeki bir engagement'ın durumunu değiştirmek
So that çalışma süreç boyunca ilerleyebilsin (onaya sun → aktifleştir/reddet → iptal et)

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given DRAFT bir engagement, `institution_id` dolu, çağıran TALENT (kendi engagement'ı) veya ORG:MEMBER (kendi org'u), When `POST /engagements/{id}/transitions` `{to_status:"PENDING_APPROVAL", version:1}` ile çağrılır, Then `200` döner, `status:"PENDING_APPROVAL"`, `version:2`, aynı transaction'da AuditEvent + outbox (koordinatör bildirimi) yazılır.
2. [Critical] Given PENDING_APPROVAL bir engagement, çağıran engagement'ın `institution_id`'sindeki INST:COORD, When `{to_status:"ACTIVE", version:2}` ile çağrılır, Then `200`, `status:"ACTIVE"`.
3. [Critical] Given PENDING_APPROVAL bir engagement, çağıran ilgili INST:COORD, When `{to_status:"REJECTED", version:2, reason:"..."}` ile çağrılır, Then `200`, `status:"REJECTED"` (terminal).
4. [Critical] Given ACTIVE bir engagement, çağıran ORG:ADMIN (kendi org'u) veya INST:COORD (kendi kurumu), When `{to_status:"CANCELLED", version:N, reason:"..."}` ile çağrılır, Then `200`, `status:"CANCELLED"` (terminal).
5. [Critical] Given herhangi bir durum, When geçiş tablosunda tanımlı olmayan bir `to_status` istenir (ör. `DRAFT→VERIFIED`), Then `422 ILLEGAL_TRANSITION`, mevcut status değişmez.
6. [Critical] Given T1, `institution_id` NULL olan bir engagement, When `PENDING_APPROVAL`'a geçiş denenir, Then `422 PRECONDITION_FAILED` (institution_id zorunlu).
7. [Critical] Given T3/T6, `reason` boş/eksik, When geçiş denenir, Then `422 PRECONDITION_FAILED`.
8. [Critical] Given kaynağa erişimi olan (kendi engagement'ı/org'u/kurumu) ama bu geçişi yapma yetkisi olmayan aktör (ör. TALENT kendi engagement'ında T2 dener), When geçiş istenir, Then `403 FORBIDDEN` (bu uç, projenin genel 404-not-403 kuralının kasıtlı istisnasıdır — bkz. STATE_MACHINE.md §4.3/API.md §2.6).
9. [Critical] Given `version` isteği gerçek DB değerinden eski, When geçiş denenir, Then `409 CONFLICT`, status değişmez.
10. [Critical] Given engagement id sistemde hiç yok, When geçiş denenir, Then `404`.
11. [High] (AC-S2) Given kaynağa (başka kurumun/org'un engagement'ı) hiç erişimi olmayan principal, When geçiş denenir, Then `404` (403 DEĞİL — bu durumda kaynağın varlığı bile bilinmiyor, madde 8'den farklı: `scoped_engagements()` bu id'yi hiç döndürmüyor).
12. [Critical] (AC-S1) Given ACTIVE bir engagement (version=5), When iki eşzamanlı istek aynı `version:5` ile farklı geçişler dener, Then sadece biri `200` alır (version→6), diğeri `409 CONFLICT` alır — DB'nin atomik `UPDATE ... WHERE version=:expected` garantisi.
13. [Critical] (AC-S3) Given TALENT rolündeki kullanıcı kendi engagement'ında, When `to_status:"ACTIVE"` (T2, sadece INST:COORD yapabilir) dener, Then `403 FORBIDDEN`, status değişmez.
14. [Medium] (AC-S4) Given herhangi bir principal, When `version` alanına gerçek DB değerinden düşük/eski bir sayı gönderir (version tampering denemesi), Then `409 CONFLICT`, durum makinesi "atlatılamaz".
15. [High] Given T3 (REJECTED) veya T6 (CANCELLED) geçişi başarıyla tamamlanır, When `reason` gönderilmiş, Then `reason` engagement satırına kalıcı olarak yazılır (`engagements.reason` kolonu) — red-team'de bulunan boşluk: `reason` önceden hiçbir yerde saklanmıyordu (ne engagement satırında ne audit/outbox'ta), bu AC ile kapatıldı.

## Threat Model
Çağrıldı — AC-S1..AC-S4 yukarıdaki Acceptance Criteria'ya eklendi (STRIDE-lite: Tampering — `version` client'tan gelir ama DB'nin atomik `WHERE version=:expected` UPDATE'i ile server-side zorlanıyor, tamper denemesi 409'a düşüyor; Elevation — yetki `can_transition()` ile institution_id/organization_id eşleşmesine göre sunucuda kontrol ediliyor, `principal.kind` tek başına yeterli değil; Info disclosure — 403/404 ayrımı kasıtlı ve dokümante, kaynağa erişimi olmayan principal'a 404 ile kaynak varlığı sızdırılmıyor). Spoofing mevcut auth altyapısı tarafından karşılanıyor. Repudiation zaten temel gereksinim (her geçiş AuditEvent üretir, istisnasız — STATE_MACHINE.md §4.1). DoS: rate limit yok, kabul edilen risk (Risks bölümünde). Yetkilendirme AC'leri üretildiği için `test-copilot`/`plan` aşamasında `authz-test` skill'i de çağrılmalı.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (T1) | `200` + `{"id":"...","status":"PENDING_APPROVAL","version":2,"talent_id":"...","organization_id":"...","institution_id":"...","updated_at":"2026-09-23T10:00:00Z"}` | `UPDATE engagements SET status=..., version=version+1 WHERE id=... AND status='DRAFT' AND version=1` + aynı tx'te `audit_event` + `outbox` (koordinatör bildirimi) INSERT | Güncel engagement objesi | AC-1 |
| 2 | Tabloda olmayan geçiş | `422` + `{"code":"ILLEGAL_TRANSITION","message":"...","request_id":null}` | Yok | Hata mesajı | AC-5 |
| 3 | Ön koşul sağlanmıyor (institution_id NULL / reason boş) | `422` + `{"code":"PRECONDITION_FAILED","message":"...","request_id":null}` | Yok | Hata mesajı | AC-6, AC-7 |
| 4 | Geçiş var, aktör yetkisiz (kaynağa erişimi var) | `403` + `{"code":"FORBIDDEN","message":"...","request_id":null}` | Yok | Yetkisiz hatası | AC-8, AC-S3 |
| 5 | `version` eski | `409` + `{"code":"CONFLICT","message":"...","request_id":null}` | Yok | "Kayıt değişti, yeniden yükleyin" | AC-9, AC-S1, AC-S4 |
| 6 | Kaynak hiç yok | `404` + `{"code":"NOT_FOUND","message":"...","request_id":null}` | Yok | "Bulunamadı" | AC-10 |
| 7 | Kaynağa hiç erişimi yok | `404` (403 DEĞİL) + aynı şema | Yok | "Bulunamadı" (kaynak varlığı sızdırılmaz) | AC-11, AC-S2 |
| 8 | Dış bağımlılık hatası (DB) | `500`, genel mesaj | Transaction tamamen rollback (`get_session` garantisi) | "Sunucu hatası" | — |
| 9 | T3/T6 başarılı, reason verilmiş | `200` + response'da `reason` alanı | `engagements.reason` kolonuna aynı transaction'da UPDATE | Kaydedilen gerekçe | AC-15 |

Kısmi başarı: status UPDATE + AuditEvent INSERT + outbox INSERT **tek transaction'da**. Biri başarısız olursa tümü rollback edilir — status DEĞİŞMEZ, istemciye 500 döner. "Kısmi başarı" senaryosu mimari olarak yok (tek commit sınırı).

Hiçbir şey yapılamadı ama hata yok: **Yok** — her istek ya `200` (status değişti) ya bir hata koduyla (403/404/409/422/500) sonuçlanır.

Boş sonuç ↔ hata ayrımı: N/A — bu bir mutation ucu, liste/okuma değil.

## Test Strategy
Unit: 70% — transition tablosu mantığı (4 geçiş + tabloda-olmayan), ön koşul kontrolleri, yetki kontrolü (institution/organization eşleşmesi)
Integration: 25% — gerçek DB'ye karşı optimistic locking (409 senaryosu, eşzamanlı istek simülasyonu), tenant isolation (404 senaryosu)
E2E: 5% — tek happy-path zinciri (DRAFT→PENDING_APPROVAL→ACTIVE→CANCELLED)

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (4 geçiş + her hata dalı küçük ve kritik bir fonksiyon, düşük hedef kabul edilemez)
Performance Target: <200ms (proje genel hedefi, bu uca özel ayrık eşik yok)
Memory: —
Görsel/UI kriteri: yok (backend-only, frontend 2.11'de)
Diğer: `pytest tests/authorization -q` tamamı yeşil kalmalı (yetkilendirme mantığı değişikliği — CLAUDE.md kuralı gereği zorunlu)

## Kapsam Dışı
- T4 (DRAFT→ACTIVE, koordinatörsüz) — STATE_MACHINE.md'nin kendi açık sorusu, MVP'de gerçeklenmiyor
- T5, T7, T8, T9, T10 — Deliverable/Evaluation/VerifiedExperience/SkillSignal/Attestation henüz yok (PLAN 2.4, 2.7, 2.8, 2.9)
- `GET /engagements/{id}` + `available_transitions[]` alanı — ayrı görev
- `DELETE /engagements/{id}` (DRAFT silme) — ayrı görev
- Frontend (PLAN 2.11)
- Bildirimin gerçek teslimi (outbox'a yazmak bu görevin kapsamında, worker'ın e-posta göndermesi değil)

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/engagements.py` — yeni route `POST /{id}/transitions`
- `backend/app/services/engagement.py` — yeni `transition_engagement()` fonksiyonu (transition tablosu, ön koşul kontrolü, optimistic locking UPDATE, AuditEvent + outbox insert)
- `backend/app/services/authorization.py` — geçiş-özel yetki kontrolü (institution_id/organization_id eşleşmesine göre) — **yetkilendirme mantığı değişikliği, CLAUDE.md gereği açık onay gerekli**
- **Yeni migration GEREKMEZ** — `status`, `version` kolonları ve CHECK kısıtları PLAN 2.1'de zaten var (teyit edildi)
- `audit_events`, `outbox` tabloları PLAN 1.2/1.5'te zaten var (varsayım, doğrulanacak)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
`yetkin360/` ile sınırlı tutulmalı (bkz. önceki görevlerde doğrulandı).

## Rollback Beklentisi
Tüm geçiş (UPDATE + AuditEvent INSERT + outbox INSERT) tek DB transaction'ında; herhangi bir adım başarısız olursa `get_session`'ın exception-handler'ı otomatik rollback yapar — kısmi state DB'ye asla yazılmaz. Servis fonksiyonu ara `flush()` yapıp farklı bir koşulda hata fırlatmamalı (2026-09-22 postmortem dersi).

## Risks
- Rate limiting yok — MVP kapsamı, kabul edilen risk (diğer uçlarla tutarlı).
- `reason` alanı (T3/T6) serbest metin — `audit_event`'e loglanırken PII guard'ı bunu yakalamaz, servis kodu `reason`'ı audit metadata'sına koymamalı (yet-2.1'deki aynı desenle tutarlı önlem).
- Yetkilendirme mantığı (`can_transition()` benzeri) ilk kez yazılıyor — `authz-test` ile doğrulanmalı.

## Assumptions
- T1'in `institution_id` ön koşulu: transition isteğine `institution_id` alanı EKLENMEZ (API.md §2.6 şeması `to_status`/`version`/`reason` dışında alan içermiyor) — engagement'ın zaten `institution_id`'si dolu olmalı (PLAN 2.1'de oluşturma sırasında set edilmiş olmalı). `institution_id` NULL bir engagement T1'i hiç yapamaz — bu bir kilitlenme değil, T4'ün (platform dışı işbirliği) bu görevde kasıtlı olarak kapsam dışı bırakılmasının doğal sonucu.
- `audit_events` ve `outbox` tabloları zaten mevcut (PLAN 1.2/1.5) — doğrulanacak, code-copilot aşamasında.

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → çoklu aktör, tek uç (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
2. Hedef → zincir bu uç olmadan çalışmaz (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3. Happy path (T1) → yukarıdaki JSON (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
4. Edge case'ler → AC-5/6/9 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Davranış sözleşmesi tablosu → yukarıda, tam doldurulmuş (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
6. Benchmark → coverage ≥90%, performans hedefi yok (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
7. Kapsam dışı → yukarıda listelendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Bağımlılıklar → yeni migration gerekmez, teyit edildi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Güvenlik kısıtı → reason PII riski, yetkilendirme testi zorunlu (Sonnet 5 low alt-ajanı tarafından yanıtlandı) — threat-model'de AC-S1..S4'e genişletildi
10. Rollback → tek transaction, get_session garantisi (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Kabul kriteri sahibi → belirtilmemiş, otomatik test + PR reviewer varsayımı (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
12. Test stratejisi → 70/25/5 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
13. T1 institution_id çelişkisi → API.md şeması institution_id almıyor, engagement zaten dolu olmalı — kullanıcıya sorulmadan API sözleşmesinden çözüldü (kesin kanıt vardı, tahmin değil)
14. threat-model tetikleyici → var (yetkilendirme mantığı değişikliği, çok-kiracılı sınır) → AC-S1..S4 üretildi
