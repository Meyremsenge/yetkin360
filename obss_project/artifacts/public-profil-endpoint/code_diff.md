# Code Diff — public-profil-endpoint (green step)

## Oluşturulan Dosyalar
- `backend/app/api/public.py` — `GET /public/talents/{slug}` router, auth-free (sadece `Depends(get_session)`)
- `backend/app/services/visibility_service.py` — `filter_public_experiences()` saf fonksiyon

## Değiştirilen Dosyalar
- `backend/app/services/authorization.py` — `scoped_public_talent_profile(session, slug)` eklendi: tek `Select`, `public_slug == slug AND visibility == 'PUBLIC' AND deleted_at IS NULL` — timing side-channel'a karşı tek sorgu.
- `backend/app/main.py` — `public_router` import + `include_router` (mevcut desene uygun, tek satır ekleme).

## AC Karşılama (Read ile doğrulandı)
| AC | Kod | Durum |
|---|---|---|
| AC-1 | `public.py:52-103` — 200 + talent_id/display_name/verified_experiences | ✓ |
| AC-2/AC-3/AC-6 | `scoped_public_talent_profile` None → aynı `HTTPException(404, "Not found")` | ✓ tek kod yolu, dallanma yok |
| AC-4 (AC-S2) | `PublicTalentProfileResponse` whitelist şema — email/user_id/institution_id yok | ✓ |
| AC-5 (AC-S3) | `filter_public_experiences()` — sadece visibility='PUBLIC' deneyimler | ✓ |
| AC-7 | try/except eklenmedi — mevcut projede global exception handler yok, FastAPI varsayılan 500'e düşer (mevcut diğer route'larla tutarlı) | ✓ |

## CAVEMAN Self-Review
- 2 yeni dosya, 1 yeni servis fonksiyonu, 1 yeni scoped_* fonksiyonu — hepsi AC'lere doğrudan bağlı, fazlalık yok.
- Çıplak `select(TalentProfile)` yok — `scoped_public_talent_profile()` üzerinden.

## Bulgular (red-team'e not, blocking değil)
1. **`VerifiedExperience` sorgusu `scoped_*()` deseninde değil** (`public.py:87-91`, `session.query(VerifiedExperience).filter(...)`) — talent_id zaten `scoped_public_talent_profile` ile doğrulandıktan SONRA çalışıyor, filtreleme Python tarafında (`filter_public_experiences`) yapılıyor. Güvenlik açığı değil (private deneyimler response'a hiç girmiyor) ama proje kuralının ("çıplak select yasak") harfine tam uymuyor — `verify`/`red-team` değerlendirsin.
2. **`started_on_snapshot`/`ended_on_snapshot` tipi `str | None`** ama model alanı `date | None` — Pydantic v2'nin `date`→`str` coercion'ı garanti değil, gerçek tarih değeri olan bir deneyimde 500/validation error riski var. `verify` adımında testler çalıştırılınca bu netleşecek.
3. `PublicVerifiedExperienceResponse.from_orm(...)` deprecated (Pydantic v2) — ama `app/api/me.py`'de zaten aynı desen kullanılıyor, projede tutarlı, yeni bir sorun değil.

## Durum
Testler henüz çalıştırılmadı (bu adımın işi değil) — sıradaki adım `verify`.
