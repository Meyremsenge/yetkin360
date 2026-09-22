---
task_slug: skill-taksonomisi-seed-arama
jira_id: YET-10
saga_task_id: null
priority: medium
threat_model: done
coverage_target: 85
performance_target: "<300ms (arama ucu, gate değil, gözlem)"
memory_target: null
test_strategy:
  unit: 65
  integration: 30
  e2e: 5
affected_modules:
  - backend/app/models/skill.py (var, değişmeyecek)
  - backend/scripts/seed.py (yeni)
  - backend/scripts/__init__.py (yeni)
  - backend/app/api/skills.py (yeni router)
  - backend/app/services/skill.py (yeni servis)
  - backend/app/services/authorization.py (scoped_skills() eklenecek)
  - backend/app/schemas/skill.py (yeni DTO'lar)
  - backend/tests/authorization/test_skill_authorization.py (yeni)
---

# ATDD — skill-taksonomisi-seed-arama

## Jira Kaynağı
[YET-10 — [PLAN 1.10] Skill taksonomisi (~150 skill) seed + arama ucu](https://kuyusuzyusuf123.atlassian.net/browse/YET-10)

User Story (Jira'dan birebir): "As any user declaring or searching skills, I want a consistent ~150-item skill taxonomy with a search endpoint, So that competency claims are comparable across the platform instead of free-text noise"

Açıklama (Jira'dan birebir): "PLAN.md Faz 1, madde 1.10. Owner: backend-1. ~150 skill'lik taksonomi seed script'i (python -m scripts.seed) + arama ucu. Production'da seed script'i çalıştırılmaz (README notu)."

Öncelik (Jira): Medium. Etiketler: backend-1, faz1.

Not: Jira'ya bu oturumda IP kısıtlaması nedeniyle API üzerinden erişilemedi ("You don't have permission to connect from this IP address"); kullanıcının paylaştığı YET-10 ekran görüntüsü kaynak alındı.

## Persona
Herhangi bir authenticated kullanıcı — talent (yetkinlik beyan eden/arayan), institution coordinator, organization member. Skill taksonomisi global referans veridir, rol bazlı filtre yok; kimliksiz (public) erişim kapalı.

## Hedef (Neden)
Serbest metin yerine karşılaştırılabilir, tutarlı bir yetkinlik taksonomisi sunmak — beyan ve arama platform genelinde aynı referans kümesine dayansın, yetkinlik beyanları arasında karşılaştırma yapılabilsin.

## User Story
As a authenticated kullanıcı (talent/coordinator/org member)
I want tutarlı bir ~150 kayıtlık skill taksonomisinde arama yapabilmek
So that yetkinlik beyanımı serbest metin yerine standart bir referansa bağlayabilirim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given authenticated bir kullanıcı, When `GET /skills/search?q=python` çağrılırsa, Then 200 döner ve `{"items": [{"id","slug","name_tr","name_en","category","status"}], "total": N}` şeklinde, `name_tr` alfabetik sıralı, eşleşen skill listesi döner.
2. [Critical] Given authenticated bir kullanıcı, When `q` parametresi verilmez veya 2 karakterden kısa gönderilirse, Then 400 döner (Pydantic `min_length=2` validasyonu).
3. [High] Given authenticated bir kullanıcı, When arama sorgusuna hiçbir skill eşleşmezse, Then 200 + `{"items": [], "total": 0}` döner (404 değil — kaynağın kendisi var, sadece eşleşme yok).
4. [High] Given bir skill `status=MERGED` ise, When arama sonucuna dahil edilirse, Then response'da `merged_into_id` (ve hedefin slug/name'i) döner; `status=DEPRECATED` olan skill'ler arama sonuçlarına hiç dahil edilmez.
5. [Critical] Given kimliksiz (token yok/geçersiz) bir istek, When `/skills/search` çağrılırsa, Then 401 döner (mevcut `get_current_user` davranışı, bkz. Davranış Sözleşmesi notu).
6. [High] Given seed script boş bir veritabanında çalıştırılırsa, When `python -m scripts.seed` çalışırsa, Then `skills` tablosuna en az 100, en fazla 200 kayıt eklenir; her kaydın `slug` benzersiz, `category` CHECK constraint'ine uygun.
7. [High] Given seed script dolu bir veritabanında (skill'ler zaten mevcut) tekrar çalıştırılırsa, When `python -m scripts.seed` çalışırsa, Then script hata vermeden (exit code 0) biter, mevcut kayıtlar değişmez, yeni satır eklenmez (idempotent, `ON CONFLICT (slug) DO NOTHING`).
8. [Medium] Given seed script çalışırken bir hata oluşursa (ör. geçersiz kategori), When script yarıda kesilirse, Then transaction rollback olur — DB'de kısmi veri kalmaz, ya tamamı yazılır ya hiçbiri.
9. [High] **(AC-S1, threat-model)** Given authenticated kullanıcı, When `q` parametresine ILIKE wildcard karakterleri (`%`, `_`) içeren bir sorgu gönderilirse, Then sorgu SQLAlchemy `ilike()` ile parametrize çalışır (ham string interpolation yok), sistem hata vermez/yavaşlamaz.
10. [Medium] **(AC-S2, threat-model)** Given DB bağlantı hatası oluşursa, When `/skills/search` çağrılırsa, Then 500 döner, yanıt gövdesinde stack trace/DB hata detayı bulunmaz (generic mesaj, detay loglanır — PII/DB detayı log'a da yazılmaz).
11. [High] **(AC-S3, threat-model)** Given `q` 200 karakterden uzun veya `limit` aşırı büyük (>100) gönderilirse, When istek yapılırsa, Then 400 döner (Pydantic `max_length`/`limit` üst sınır validasyonu).

## Agentic Değerlendirme Kriterleri
(Tetikleyici yok — bu görev bir LLM agent/sub-agent tool-calling davranışı veya prompt'u değiştirmiyor. Bölüm silindi.)

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: `GET /skills/search?q=python` | 200 + `{"items":[...], "total": N}` | Yok (salt okuma) | Eşleşen skill listesi, alfabetik sıralı | AC-1 |
| 2 | Girdi geçersiz/eksik (`q` yok veya `len(q)<2`) | 400 + Pydantic validation error body | Yok | "q alanı en az 2 karakter olmalı" | AC-2 |
| 3 | Kaynak yok (arama sonucu boş) | 200 + `{"items":[], "total":0}` | Yok | Boş liste, hata değil | AC-3 |
| 4 | Yetkisiz erişim (token yok/geçersiz) | 401 (mevcut `get_current_user` davranışı — kaynağın kendisi genel/global, CLAUDE.md'nin 403→404 kuralı *belirli bir kaynağa* yetkisiz erişim için; burada kimlik doğrulama hiç yok) | Yok | "Giriş yapmalısınız" | AC-5 |
| 5 | Dış bağımlılık hatası (DB bağlantı hatası) | 500, generic hata mesajı | Hata loglanır (PII/DB detayı olmadan) | Genel hata mesajı | AC-10 (AC-S2) |
| 6 | Zaman aşımı | **Uygulanmaz — MVP'de ayrı timeout mekanizması kurulmaz.** Gerekçe: ~150 satırlık indexed ILIKE sorgusu için ayrı timeout gereksinimi yok; bu görev kapsamında yeni bir timeout katmanı yazmak over-engineering olur. | — | — | — |
| 7 | **Kısmi başarı** (seed script yarıda hata alırsa) | Script exit code ≠ 0; toplu insert transaction içinde, hata durumunda rollback — DB'de kısmi veri kalmaz | Yok (rollback) | Konsolda hata mesajı + traceback | AC-8 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** (tablo zaten dolu, tekrar çalıştırılırsa) | Script exit code 0, `ON CONFLICT DO NOTHING` ile mevcut kayıtlar atlanır | DB değişmez (yeni satır yok) | Konsolda "N skill zaten mevcut, 0 yeni kayıt eklendi" bilgi mesajı | AC-7 |

Kısmi başarı: Seed script tek transaction içinde çalışır — bir kısmı yazılıp kalanı hata verirse tamamı rollback olur, DB'de tutarsız/yarım veri kalmaz.
Hiçbir şey yapılamadı ama hata da yok: Seed script'in mevcut kayıtları atlaması (idempotent upsert) sessiz bir "başarı" değil — konsola "0 yeni kayıt eklendi" mesajı basılır, çağıran bunu gözlemleyebilir.
Boş sonuç ↔ hata ayrımı: Arama sonucu boşsa 200 + boş liste (kaynak var, eşleşme yok); kimlik doğrulama yoksa 401 (kaynağa hiç erişilemedi); DB hatasında 500 (sistem hatası) — üçü farklı durum kodlarıyla ayrılır, aynı değeri döndürmezler.

## Test Strategy
Unit: 65% — seed script'in veri üretim/validasyon mantığı, arama query-building fonksiyonu, Pydantic şema validasyonları
Integration: 30% — gerçek DB üzerinden seed idempotency, arama endpoint'i + authorization akışı (scoped_skills, get_current_principal)
E2E: 5% — az sayıda smoke test (tam HTTP request/response happy path)

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: <300ms (arama ucu — gate değil, gözlem; ~150-200 satırlık indexed ILIKE için kolay ulaşılır bir üst sınır)
Memory: —
Görsel/UI kriteri: Yok (bu görev backend-only, frontend kapsamı dışında)
Diğer ölçülebilir kriterler: Seed script sonrası `skills` tablosunda 100-200 arası kayıt, her biri `slug` UNIQUE ve `category` CHECK constraint'ine uygun.

## Kapsam Dışı
- Skill CRUD endpoint'i (create/update/delete) — sadece seed (script) + arama (GET) var.
- Skill merge/deprecate işlemi için yönetim arayüzü/endpoint'i — model alanları var, bu görevde işletilmiyor, seed verisiyle statik set edilebilir.
- `talent_skills` / skill beyanı tablosu ve ilişkili endpoint'ler — PLAN 1.11 kapsamında ("Talent yetkinlik beyanı: skill ekle/listele/çıkar").
- AI tabanlı skill önerisi, otomatik eşleştirme, fuzzy/semantic search (embedding, pgvector) — MVP dışı yasaklı (final analiz §39).
- Skill kategorisi/hiyerarşisi düzenleme arayüzü — yok.
- Rate limiting — bu görev kapsamında yeni rate-limit altyapısı kurulmayacak (bkz. Risks).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/skill.py` — var, değişmeyecek (şema zaten hazır: id, slug, name_tr, name_en, category, parent_id, status, merged_into_id).
- `backend/scripts/seed.py` + `backend/scripts/__init__.py` — yeni, `python -m scripts.seed` komutuyla çalışacak.
- `backend/app/api/skills.py` — yeni router (`GET /skills/search`).
- `backend/app/services/skill.py` — yeni servis (arama iş mantığı, router'da değil).
- `backend/app/services/authorization.py` — `scoped_skills()` eklenecek (global veri olsa da "çıplak select(Model) yasak" kuralı gereği merkezi scoped select).
- `backend/app/schemas/skill.py` — `SkillResponse`, `SkillSearchResponse` DTO'ları.
- `backend/tests/authorization/test_skill_authorization.py` — yeni yetkilendirme testi (auth yoksa 401, authenticated ise 200).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git reposunun kökünün proje klasörüyle aynı olup olmadığı teyit edilmedi. Sonraki adımlarda (plan/code-copilot/test-copilot/red-team) arama `C:\Users\Meyrem\Desktop\P\yetkin360` ile sınırlı tutulmalı; sınırsız arama (`git log -p --all`, kök dizinden `grep -r`) yapılmamalı.

## Rollback Beklentisi
Seed script: transaction içinde çalışır, hata durumunda tam rollback (kısmi veri kalmaz). Arama endpoint'i salt-okunur, rollback senaryosu yok. Migration gerekmiyor (şema zaten mevcut) — bu görevde migration rollback'i kapsam dışı.

## Risks
- Rate limit bu endpoint'te yok — PLAN 1.6 notunda genel rate-limit altyapısı henüz kurulmamış ve bu görev kapsamında da kurulmayacak, ertelenmiş bir karar olarak kabul ediliyor. (threat-model DoS değerlendirmesi: kabul edilen risk)
- Auth-yok durumunda 401 dönmesi, CLAUDE.md'nin "403 yerine 404" kuralıyla küçük bir nüans taşıyor — mevcut `get_current_user` (backend/app/core/deps.py) davranışı zaten 401 döndürüyor, bu görev yeni bir sapma yaratmıyor, mevcut altyapıya uyum sağlıyor.

## Assumptions
- Arama sıralaması relevance skorlama değil, alfabetik (`name_tr ASC`) — relevance/fuzzy arama motoru sayılabilecek kapsam riski taşır, MVP'de basit ILIKE + alfabetik yeterli kabul edildi. (Sonnet 5 low alt-ajanı varsayımı)
- Sayfalama `limit`/`offset` ile MVP'den itibaren var (varsayılan limit=20, max=100) — 150 kayıt küçük olsa da tutarlılık için baştan eklendi. (Sonnet 5 low alt-ajanı varsayımı)
- MERGED skill'lerin arama sonucuna dahil edilip `merged_into_id` ile yönlendirme bilgisi dönmesi — üründe teyit edilmemiş, model alanının anlamlı kullanımı olarak varsayıldı. (Sonnet 5 low alt-ajanı varsayımı)
- Seed script'in tek transaction içinde toplu insert yapması varsayıldı — CLAUDE.md'nin "ağ çağrısı transaction dışı" kuralı bu işlem için geçerli değil (DB-only, ağ çağrısı yok).
- Kabul kriteri sahibi: otomatik test (pytest yeşil) yeterli kabul edildi; PO/owner (backend-1) nihai gözden geçirme yapabilir ama bu bir varsayım, teyit edilmedi.

## Unknowns
- ~150 skill'lik gerçek taksonomi verisinin (isim TR/EN, kategori, hiyerarşi) kaynağı belirsiz — elle mi derlenecek yoksa bir standarttan (ör. ESCO, O*NET) mi uyarlanacak? Jira/PLAN.md/final-analiz'de açık değil. Seed script'in içeriğini doğrudan etkiliyor, iş başlamadan backend-1 veya ürün sahibiyle netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → Tüm authenticated kullanıcılar (talent, coordinator, org member), public değil (Sonnet 5 low alt-ajanı tarafından yanıtlandı: taksonomi global veri, auth zorunlu — tutarlılık + MVP basitliği)
2. Ana hedef/neden → Jira'dan birebir (kullanıcı mesajından/Jira)
3. Happy path senaryosu → `GET /skills/search?q=...`, `{"items":[...],"total":N}`, limit/offset sayfalama, alfabetik sıralama (Sonnet 5 low alt-ajanı tarafından yanıtlandı: relevance scoring kapsam riski taşır)
4. Edge case — boş/kısa query → 400, min_length=2 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
5. Edge case — sonuç bulunamazsa → 200 + boş liste, 404 değil (Sonnet 5 low alt-ajanı tarafından yanıtlandı: CLAUDE.md'nin 404 kuralı yetkisiz erişim için)
6. Edge case — MERGED/DEPRECATED skill'ler → MERGED dahil+yönlendirme, DEPRECATED hariç (Sonnet 5 low alt-ajanı tarafından yanıtlandı, not: varsayım olarak işaretlendi)
7. Davranış sözleşmesi tablosu → dolduruldu (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8. Başarı ölçütü/benchmark → coverage 85%, performans <300ms gözlem (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
8b. Seed tam sayı mı aralık mı → 100-200 aralığı, tam sayı test edilmez (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Kapsam dışı → CRUD/merge-UI/talent_skills/AI eşleştirme/rate-limit (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
10. Bağımlılıklar/etkilenen dosyalar → önerilen liste onaylandı (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Performans/güvenlik kısıtı → SQL injection: ORM parametrize zorunlu; rate limit: ertelendi (Sonnet 5 low alt-ajanı tarafından yanıtlandı) — threat-model skill'i tarafından AC-S1/S2/S3 olarak somutlaştırıldı
12. Rollback beklentisi → idempotent upsert, `ON CONFLICT DO NOTHING`, sadece dev/test+bootstrap için (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
13. Kabul kriteri sahibi → otomatik test yeterli (Sonnet 5 low alt-ajanı tarafından yanıtlandı, varsayım olarak işaretli)
14. Test stratejisi oranı → unit 65/integration 30/e2e 5 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
15. Bilinen riskler/varsayımlar → taksonomi veri kaynağı Unknown (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
16. Threat-model (STRIDE-lite) → AC-S1 (ILIKE wildcard/parametrize sorgu), AC-S2 (DB hata mesajı sızıntısı yok), AC-S3 (q/limit üst sınır) — `threat-model` skill'i tarafından üretildi, rate-limit kabul edilen risk olarak işaretlendi
