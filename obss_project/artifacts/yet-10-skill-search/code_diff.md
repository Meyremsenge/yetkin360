# Code Diff — yet-10-skill-search
_Green step — Haiku alt-ajanı tarafından yazıldı, orkestratör tarafından
`Read`+gerçek doğrulama ile kontrol edildi_

## Oluşturulan dosyalar
- `backend/app/api/skills.py` — `GET /skills` router (`q?`, `category?`,
  `limit?` → `{items:[...]}`), `SkillCategory` enum, `SkillItemResponse`/
  `SkillListResponse` (ORM modeli doğrudan dönülmüyor).
- `backend/app/services/skill.py` — `search_skills(session, q, category,
  limit)`, tek merkezi filtreli sorgu (plan.md Kararlar #1'e uygun).
- `backend/scripts/__init__.py` (boş, paket işareti).
- `backend/scripts/seed.py` — 36 temsili skill (LANGUAGE 8, FRAMEWORK 8,
  TOOL 8, DOMAIN 6, SOFT 6), idempotent (`slug` var mı kontrolü).

## Değiştirilen dosyalar
- `backend/app/main.py` — `skills_router` eklendi (diğer router'larla aynı
  kalıp).

## İlk turda bulunan ve düzeltilen sorunlar
- Lint: `app/api/skills.py`'de kullanılmayan `Skill` import'u — kaldırıldı.
- Mypy: `search_skills()`'in dönüş tipi `list[Skill]` olarak bildirilmişti
  ama SQLAlchemy 2.0'da `session.execute(...).scalars().all()` gerçekte
  `Sequence[Skill]` döndürüyor — imza `Sequence[Skill]` olarak düzeltildi.
- **Doğrulama sırasında bulunan (orkestratör kaynaklı) yan etki:** Seed
  script'ini gerçekten çalıştığını doğrulamak için bizzat çalıştırdım —
  bu, paylaşılan dev veritabanına 36 gerçek satır (`slug='python'` vb.)
  ekledi. Test fixture'ları aynı slug'larla kendi (savepoint içinde)
  kayıtlarını oluşturmaya çalışınca `UniqueViolation` ile 32 test hata
  verdi. Kök neden implementasyon hatası değildi — orkestratörün doğrulama
  adımının kendisiydi. `docker exec ... psql DELETE FROM skills WHERE
  slug IN (...)` ile 36 satır temizlendi, testler tekrar çalıştırılıp
  37/37 PASS olduğu doğrulandı. **Ders:** seed script'i gerçek DB'ye karşı
  doğrulanırken, doğrulama sonrası eklenen veri mutlaka temizlenmeli —
  `postmortem`'e not düşülecek.

## Migration
Yok — `Skill` tablosu zaten mevcut (YET-1), şema değişmedi.

## Acceptance Criteria doğrulaması (Read + pytest ile)
| AC | Durum | Not |
|---|---|---|
| AC-1 | ✅ | `search_skills` ILIKE ile `name_tr`/`name_en`/`slug` üzerinde arar, `status='ACTIVE'` filtreli |
| AC-2 | ✅ | `q` yoksa varsayılan `limit=50` |
| AC-3 | ✅ | Sonuç yoksa `{"items":[]}`, `200` |
| AC-4 | ✅ | `category` filtresi `Skill.category == category` |
| AC-5 | ✅ | `SkillCategory` Pydantic enum → geçersiz değer `422` |
| AC-6 | ✅ | `Query(gt=0, le=100)` → aşan/negatif değer `422` |
| AC-7 | ✅ | `search_skills` her zaman `status=='ACTIVE'` ile başlıyor, MERGED/DEPRECATED asla dönmez |
| AC-8 | ✅ | `get_current_user` dependency zaten `401` döndürüyor |
| AC-9 | ✅ | `scripts/seed.py` gerçekten çalıştırılıp doğrulandı: ilk çalıştırma 36 ekledi, ikinci çalıştırma 0 ekledi (idempotent) — sonra DB temizlendi |
| AC-S1 | ✅ | `SkillItemResponse`'da `status`/`merged_into_id`/`created_at`/`updated_at` yok |
| AC-S2 | ✅ | SQLAlchemy ORM `.ilike()`/`.where()` — ham SQL birleştirme yok, parametreli sorgu |

## CAVEMAN self-review
- Yeni dosya sayısı: 3 (router + servis + seed script) — minimum gerekli.
- Yeni soyutlama yok — tek `search_skills()` fonksiyonu, mevcut
  `talent_skills.py`/`me.py` kalıbı takip edildi.
- Seed verisi elle yazılmış, gerçekçi (DOMAIN.md §3.5 kategorilerinden).

## Test dosyalarına dokunulmadı
`git status --short` ile `tests/test_skill_search*.py`'nin code-copilot
dispatch'i sırasında değişmediği doğrulandı.

## Sonraki adım
`verify` — gerçek test çalıştırması zaten bu adımda yapıldı (37 hedefli +
335 proje geneli + 71 authorization test PASS, ruff/mypy temiz, seed script
gerçekten çalıştırılıp DB temizlendi) ama `verify` skill'i CI komutlarıyla
resmi olarak tekrar teyit edecek.
