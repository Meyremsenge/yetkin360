# Code Diff — public-dogrulama-linki

## Tur 1 — Migration (uygulandı ve doğrulandı)

### Oluşturulan
- `backend/alembic/versions/m4n5o6p7q8r9_add_public_token_to_verified_experiences.py` — `verified_experiences.public_token` (nullable, String, UNIQUE + index), `down_revision='l3m4n5o6p7q8'`

### Değiştirilen
- `backend/app/models/verified_experience.py` — `public_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)` eklendi (docstring de güncellendi)

### Doğrulama
- `alembic upgrade head` → PASS
- `alembic downgrade -1` → PASS
- `alembic upgrade head` (tekrar) → PASS
- DB şu an head'de (`m4n5o6p7q8r9`)

## Tur 2 — Servis + Endpoint

### Oluşturulan
- `backend/app/services/verified_experience.py` — `generate_public_token()` (`secrets.token_urlsafe(32)`, AC-S1). Henüz hiçbir yerden çağrılmıyor (T8 entegrasyonu kapsam dışı, atdd.md'de not düşülmüştü).

### Değiştirilen
- `backend/app/services/authorization.py` — `scoped_public_verified_experience_by_token()` eklendi (YET-105'teki `scoped_public_talent_profile` deseniyle tutarlı, tek WHERE).
- `backend/app/api/public.py` — mevcut router'a `GET /public/v/{token}` eklendi, `PublicVerificationResponse`/`AttestedSkillResponse` Pydantic modelleri.

### AC Karşılama (Read ile doğrulandı)
AC-1..AC-7 (AC-S1/S2/S4 dahil) implementasyonda karşılanmış görünüyor — `plan.md` Kararlar'a uygun (`attestor_organization`, `attestor_name` değil).

### Bulgular (red-team'e not, blocking değil)
1. **`Attestation` sorgusu `scoped_*()` deseninde değil** (`public.py`, `select(Attestation).where(engagement_id==...)`) — YET-105'teki aynı desen (VerifiedExperience naked query, sonradan red-team'de düzeltildi). Burada `ve.engagement_id` zaten `scoped_public_verified_experience_by_token` ile PUBLIC olarak doğrulanmış bir kaydın alanı, güvenlik açığı yok ama proje kuralının harfine aykırı.
2. **Potansiyel tip riski:** `PublicVerificationResponse.started_on: date` (non-nullable) ama `VerifiedExperience.started_on_snapshot` modelde `date | None` (nullable). Gerçek veride NULL bir `started_on_snapshot` varsa Pydantic `ValidationError` fırlatabilir — YET-105'te aynı sınıftan bir bug (date/str tip uyuşmazlığı) verify aşamasında ortaya çıkmıştı. `verify` adımında testler çalıştırılınca netleşecek.
3. `Engagement` importu fonksiyon içinde yapılmış (`from app.models import Engagement`), top-level import'a taşınabilir — küçük bir okunabilirlik notu.

### Durum
Testler henüz çalıştırılmadı — sıradaki adım `verify`.
