# HANDOFF — PLAN 2.7 (YET-69): Değerlendirme formu şeması

## Hedef
PLAN 2.7 / YET-69: `evaluations` + `evaluation_items` şeması (yetkinlik + davranış kriterleri,
`NOT_OBSERVED` durumu) + `POST /engagements/{id}/evaluation` ucu. Tam ATDD zinciri
(`obss_project/artifacts/yet-69-degerlendirme-formu-semasi/`) izlenerek yapıldı: atdd.md → plan.md
→ test_diff.md (red) → code_diff.md (green) → verify_report.md (KISMİ, burada kesildi).

**Bütün karar geçmişi, AC'ler, davranış sözleşmesi için önce şunu oku:**
`obss_project/artifacts/yet-69-degerlendirme-formu-semasi/atdd.md` — özellikle "Sorular ve Cevaplar"
ve "Risks" bölümleri, kullanıcıyla konuşulmuş kritik kararları taşıyor (T7 geçişinin bu göreve
dahil edilmesi, 404 vs 403 ayrımı).

## Şu Ana Kadar Yapılanlar (branch: `feature/plan-2.7-degerlendirme-formu-semasi`, henüz push edilmedi)

1. **ATDD tamamlandı ve onaylandı** — `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/atdd.md`
2. **Plan tamamlandı** — `plan.md`, gerçek kod tabanı keşfedildi, 2 açık soru çözüldü (T7 mekanizması, 403/404 ayrımı)
3. **Testler yazıldı (red step)** — `backend/tests/test_evaluation.py`, `backend/tests/test_evaluation_authorization.py` (33 test, tüm AC'ler kapsanmış — bkz. `test_diff.md`)
4. **Implementasyon yazıldı (green step)** — bkz. "Değişen/Yeni Dosyalar" aşağıda
5. **Migration uygulandı** — `alembic upgrade head` PASS, `alembic downgrade i0j1k2l3m4n5` PASS (geri alınabilirlik doğrulandı), tekrar `upgrade head` ile DB tutarlı bırakıldı. **Local dev DB şu an migration uygulanmış durumda.**
6. **Unit testler KISMİ çalıştırıldı** — 15 passed, 10 errors (bkz. "Ne İşe Yaramadı")

## Değişen/Yeni Dosyalar (implementasyon, code_diff.md'de detaylı doğrulama var)

**Yeni:**
- `backend/app/models/evaluation.py` — `Evaluation` + `EvaluationItem` ORM modelleri
- `backend/app/schemas/evaluation.py` — Pydantic DTO'lar (`EvaluationResponse`'ta `private_note` YOK — kasıtlı, AC-S1)
- `backend/app/services/evaluation.py` — `create_evaluation()` iş mantığı (T7 geçişi burada, `engagement.py`'ye dokunmadan izole edildi)
- `backend/alembic/versions/j1k2l3m4n5o6_add_evaluations_table.py` — evaluations/evaluation_items tabloları
- `backend/alembic/versions/a337f634c1d1_merge_evidence_deliverable_id_ve_.py` — merge migration (bkz. "Ne İşe Yaramadı" #1)

**Değişen:**
- `backend/app/models/__init__.py` — yeni modeller export edildi
- `backend/app/api/engagements.py` — `POST /{engagement_id}/evaluation` ucu eklendi (satır ~548-682)

**Dokunulmadı (kasıtlı):** `backend/app/services/engagement.py` — T7 geçişi `transition_table`'a eklenmedi, `create_evaluation()` içinde izole edildi. Bu, YET-88 (EVALUATED→VERIFIED, muhtemelen paralel çalışılıyor) ile olası merge çakışmasını önlüyor.

## Ne İşe Yaradı

- **ATDD/plan/test-copilot/code-copilot pipeline'ı sorunsuz işledi.** Her adımda Haiku alt-ajanının çıktısı gerçek dosya okumasıyla doğrulandı (alt-ajan özetine güvenilmedi) — bu disiplin bir migration dallanma sorununu (aşağıya bakınız) erken yakaladı.
- **Migration merge'ü:** Projede zaten emsal vardı (`045883d11996_merge_yet6...py`), aynı pattern (`alembic merge -m "..." <head1> <head2>`) kullanıldı, sorunsuz çalıştı.
- **T7 geçişini `services/engagement.py`'nin `transition_table`'ına eklemek yerine `services/evaluation.py` içinde izole etmek** — plan aşamasında öngörülen bir riski (YET-88 ile aynı dosya çakışması) fiilen ortadan kaldırdı.

## Ne İşe Yaramadı / Dikkat Edilmesi Gerekenler

1. **Migration dallanması (ÇÖZÜLDÜ ama tekrar dikkat gerektirir):** Plan aşamasında "tek alembic head" derken `1a2b3c4d5e6f_add_evidence_deliverable_id.py` dosyası gözden kaçırılmıştı (glob taramasında `tail -10` sınırına takılmıştı). Gerçekte `i0j1k2l3m4n5`'ten sonra iki dal vardı. Kullanıcı onayıyla merge migration (`a337f634c1d1`) oluşturuldu. **Ders: `alembic heads` komutunu (python script yerine) güvenip DOĞRUDAN çalıştırmak daha güvenilir olurdu — bir dahaki sefere bunu kullan.**

2. **`alembic downgrade -1` merge noktasında "Ambiguous walk" hatası verdi.** Bunun yerine `alembic downgrade <ortak-ata-revizyonu>` (örn. `alembic downgrade i0j1k2l3m4n5`) kullanmak gerekti. Bu alembic'in bilinen bir sınırlaması, CLAUDE.md'nin "alembic downgrade -1" komutuna güvenmemesi gerektiği bir proje notu olarak düşünülebilir.

3. **KRİTİK — Test fixture hatası, implementasyon hatası DEĞİL:** `pytest tests/test_evaluation.py tests/test_evaluation_authorization.py -q` → **15 passed, 10 errors**.
   Kök neden: `test_evaluation.py`'deki `skill_communication_eval` fixture'ı şunu yapıyor:
   ```python
   skill = Skill(name="Communication", description="...", category="BEHAVIORAL")
   ```
   Ama gerçek `Skill` modeli (`backend/app/models/skill.py`):
   - `name` diye bir alan YOK (gerçek alan adını kontrol et — muhtemelen farklı bir isim)
   - `category` CHECK constraint'i sadece `('LANGUAGE','FRAMEWORK','TOOL','DOMAIN','SOFT')` kabul ediyor — `"BEHAVIORAL"` GEÇERSİZ.

   Bu hata **test setup aşamasında** patlıyor, gerçek endpoint'e hiç ulaşılmadan — yani **implementasyonun (models/evaluation.py, services/evaluation.py, api/engagements.py) doğru olup olmadığı henüz kanıtlanmadı.** 15 geçen test bu fixture'ı kullanmayan testler (örn. bazı response şeması testleri), ama happy path, private_note PII testi, T7 geçiş testi gibi KRİTİK testler bu 10 hatanın içinde.

## Sıradaki Adımlar (öncelik sırasıyla)

1. **`backend/app/models/skill.py`'yi oku**, `Skill`'in gerçek alan adlarını ve `category` constraint'ini teyit et. Davranışsal kriterler muhtemelen `skill_id=None` ile temsil edilmeli (atdd.md Assumptions'ta zaten bu vardı) — yani `skill_communication_eval` fixture'ının kendisi belki hiç gerekmiyor, testler `skill_id=None` kullanarak sadeleştirilebilir.
2. `test_evaluation.py` içindeki ilgili fixture'ı/fixture'ları düzelt (10 hatalı testin hangilerinin bu fixture'a bağımlı olduğunu tara).
3. `pytest tests/test_evaluation.py tests/test_evaluation_authorization.py -v` tekrar çalıştır, **tüm 33 testin gerçekten PASS olduğunu** doğrula.
4. `ruff check .` ve `mypy app` çalıştır (bkz. `.github/workflows/ci.yml` — CI'ın kullandığı birebir komutlar), hiç çalıştırılmadı.
5. `security-scan` skill'ini çalıştır (verify'ın gate 10'u, hiç çalıştırılmadı).
6. `pytest -q` — backend'in TAM paketi (yeni migration'ın mevcut testleri bozmadığını doğrula).
7. Hepsi yeşilse `red-team` skill'ini çalıştır (bu görev için hiç başlamadı) — özellikle `private_note` sızıntısı ve 404/403 ayrımını sorgulasın.
8. `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/verify_report.md`'yi tam sonuçlarla güncelle.
9. Kullanıcıdan nihai onay al, sonra commit mesajını CLAUDE.md formatına göre yaz (`Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`, PLAN 2.7 referansıyla).

## Referans Dosyalar
- `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/atdd.md` — tüm AC'ler, davranış sözleşmesi, kullanıcı kararları
- `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/plan.md` — dosya değişiklik planı, migration taslağı
- `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/test_diff.md` — AC→test eşlemesi
- `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/code_diff.md` — implementasyon doğrulaması
- `obss_project/artifacts/yet-69-degerlendirme-formu-semasi/verify_report.md` — kısmi verify sonucu (BU görevin en güncel durumu)
- Jira: YET-69 (ana görev), YET-86 (model+migration), YET-87 (endpoint+test), YET-88 (SONRAKİ görev, EVALUATED→VERIFIED — bu görevin kapsamı DIŞINDA, muhtemelen paralel çalışılıyor)
