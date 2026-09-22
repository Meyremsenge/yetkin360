# Plan — yet-10-skill-search
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, frontend zaten var
ve değiştirilmeyecek).

## Keşif özeti
- `app/api/skills.py` yok — yeni.
- `Skill` modeli (`app/models/skill.py`) zaten var, DEĞİŞTİRİLMEYECEK.
- `backend/scripts/` dizini yok — yeni.
- Migration head'i tek (`f7e8g9h0i1j2`, YET-11'in migration'ı) — şema
  değişikliği gerekmiyor (Skill tablosu zaten var), migration GEREKMİYOR.
- `app/api/me.py`/`talent_skills.py` kalıbı: DTO'lar router içinde, hata
  sözleşmesi `{code,message,request_id}`.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/main.py` | Yeni `skills_router`'ı `include_router` ile kaydetmek. | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/app/api/skills.py` | Router: `GET /skills` (`q?`, `category?`, `limit?`, `cursor?` → `{items:[...]}`). |
| `backend/app/services/skill.py` | `search_skills(session, q, category, limit)` — merkezi filtreli sorgu (bkz. Open Questions #1). |
| `backend/scripts/__init__.py` | Boş — `python -m scripts.seed` çalıştırılabilmesi için paket işareti. |
| `backend/scripts/seed.py` | `~30-50` temsili skill'i `INSERT` eden CLI script (bkz. Open Questions #2). |
| `backend/tests/test_skill_search.py` | Fonksiyonel AC testleri (test-copilot yazacak). |
| `backend/tests/test_skill_search_authorization.py` | AC-8/AC-S1/AC-S2 testleri (test-copilot yazacak). |

## Dependencies
- `app/api/deps.py` → `get_current_user` (AUTH — `Principal` gerekmez, rol
  ayrımı yok).
- `app/models/skill.py` → `Skill` (salt okunur).
- Hata sözleşmesi: mevcut `{code,message,request_id}` deseni
  (`app/main.py`'deki handler'lar) — DEĞİŞTİRİLMEYECEK.

## Migration Required?
**Hayır** — `Skill` tablosu zaten YET-1'de oluşturuldu, şema değişmiyor. Bu
görev yalnızca (a) yeni bir okuma ucu ve (b) bir seed script'i ekliyor.

## Risks
(atdd.md'den taşınan)
- Seed script'inin `python -m scripts.seed`'in production'da yanlışlıkla
  çalıştırılması riski — script içine "bu komutu production'da çalıştırma"
  uyarısı (docstring/print) eklenmeli, ama otomatik bir ortam kontrolü
  (`ENVIRONMENT != production` gibi) MVP kapsamı dışı (CLAUDE.md kapsam
  kısıtı — gereksiz karmaşıklık).
- Seed script'i idempotent olmalı (birden fazla çalıştırılırsa `slug`
  unique constraint'i ihlal etmemeli) — `code-copilot`'a açıkça
  hatırlatılacak (`INSERT ... ON CONFLICT DO NOTHING` veya var-mı-kontrolü).

## Open Questions
1. **`search_skills()`'in çıplak `select()` ile ilişkisi:** atdd.md'nin
   Risks bölümünde önerilen çözüm (yeni bir `services/skill.py` fonksiyonu,
   içinde `select(Skill).where(status='ACTIVE', ...)`) onaylanıyor mu? Bu,
   mevcut `scoped_*()` paternine uymuyor çünkü `Skill` kiracı-özel bir
   kaynak değil — merkezi bir servis fonksiyonu üzerinden geçtiği için
   "çıplak/kontrolsüz sorgu" yasağını ihlal etmediği düşünülüyor. **Öneri:
   onayla** — CLAUDE.md kuralının amacı (rastgele yerlerde kontrolsüz veri
   erişimini önlemek) burada da sağlanıyor, sadece `scoped_*()` isimlendirme
   kalıbı uygulanmıyor (bu kaynak zaten kiracıya özel değil).
2. **Seed listesinin içeriği:** atdd.md'nin Assumptions'ında önerilen
   ~30-50 temsili skill (tam "~150" yerine) onaylanıyor mu? **Öneri:
   onayla** — DOMAIN.md §3.5'in kategori örneklerinden (LANGUAGE: Python,
   JavaScript, TypeScript, Java, Go...; FRAMEWORK: FastAPI, React, Django,
   Next.js...; TOOL: Docker, Git, PostgreSQL...; DOMAIN: Makine Öğrenmesi,
   Veri Analizi...; SOFT: İletişim, Takım Çalışması...) türetilecek, her
   kategoriden en az 6-8 örnek.

Kullanıcıdan yanıt/"sen karar ver" bekleniyor.

## Kararlar
(kullanıcı yetkisiyle Sonnet 5 low alt-ajanı tarafından yanıtlandı)
1. **`search_skills()` vs çıplak `select()`:** Onaylandı — merkezi servis
   fonksiyonu üzerinden filtreli sorgu kullanılacak.
2. **Seed listesi ~30-50:** Onaylandı — DOMAIN.md §3.5 kategorilerinden
   her birinden en az 6-8 temsili örnek.
