# Plan — yet-8-institution-koordinator-ogrenci-bagi
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, UI/component dosyası yok).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/app/services/authorization.py | `scoped_institutions()` eklenir (Principal'da `institution_ids` alanı zaten var, kullanılmıyor); `can()`'a Institution-ilişkili action'lar eklenir (AC-1..AC-5) | medium |
| docs/API.md | Yeni "Institutions" bölümü (Organization deseniyle simetrik), kod yazımından önce | low |

## New Files
| File | Purpose |
|------|---------|
| backend/app/services/institution.py | Kurum oluşturma, koordinatör davet, öğrenci-kurum bağı isteği/onayı iş mantığı |
| backend/app/api/institutions.py | HTTP router: `POST /institutions`, `POST /institutions/{id}/members`, `POST /institutions/{id}/link-requests`, `POST /institutions/{id}/link-requests/{request_id}/approve` |
| backend/app/models/institution_link_request.py | `InstitutionLinkRequest` modeli (id, talent_profile_id, institution_id, status PENDING/APPROVED/REJECTED, requested_at, decided_at, decided_by_user_id) |
| backend/alembic/versions/xxxx_institution_link_requests.py | Yeni migration — `institution_link_requests` tablosu (kullanıcı onayı alındı) |

## Dependencies
- `backend/app/services/authorization.py` — `Principal`, `can()`, `get_scoped_or_404()` (YET-2, değişmez, genişler)
- `backend/app/models/identity.py` — `Institution`, `InstitutionMember`, `TalentProfile` (mevcut, migration YOK — bkz. Migration Required?)
- `docs/API.md` §2.4 (`/organizations`) — desen referansı

## Migration Required?
**Evet — kullanıcı onayı alındı.**

`docs/DATABASE.md` ve gerçek migration (`backend/app/models/identity.py`) doğrulandı: `talent_profiles.institution_id` düz, nullable bir FK — ayrı bir "pending link request" tablosu/alanı YOK, bu yeni bir migration'la eklenecek.

**Onaylanan tasarım (Seçenek 2 — açık istek + açık onay):** Yeni `institution_link_requests` tablosu:
```
institution_link_requests
  id uuid PK
  talent_profile_id uuid NOT NULL REFERENCES talent_profiles(id)
  institution_id uuid NOT NULL REFERENCES institutions(id)
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED'))
  requested_at timestamptz NOT NULL DEFAULT now()
  decided_at timestamptz
  decided_by_user_id uuid REFERENCES users(id)
  UNIQUE (talent_profile_id, institution_id) WHERE status = 'PENDING'  -- aynı kuruma tekrar PENDING istek yok (AC-8)
```
Öğrenci `POST /institutions/{id}/link-requests` ile `PENDING` kayıt oluşturur (AC-3). Koordinatör/ADMIN `POST /institutions/{id}/link-requests/{request_id}/approve` ile onaylar → kayıt `APPROVED` olur VE `TalentProfile.institution_id` set edilir (AC-3b, tek transaction).

Migration `code-copilot` adımında (Haiku alt-ajanı tarafından, `alembic revision --autogenerate` ile) oluşturulacak — orkestratör migration dosyasını kendisi yazmaz.

## Risks
- (atdd.md'den) BOLA/tenant-leakage çekirdek risk — AC-S1/AC-S2 ile ele alınıyor, plan bunu değiştirmiyor.
- **Kapsam değişikliği:** atdd.md'nin AC-3'ü ("öğrenci-bağ isteği PENDING kalır, koordinatör onaylar") bu bulguyla uyumsuz — gerçek şema PENDING durumu desteklemiyor. AC-3 revize edilmeli: "öğrenci institution_id'yi kendi yazamaz, sadece koordinatör bir öğrenciyi kurumuna ekleyebilir/bağlayabilir" şeklinde.

## Open Questions
(Boş — Seçenek 2 (migration'lı, açık istek + açık onay) kullanıcı tarafından onaylandı. atdd.md AC-3/AC-3b ve bu dosyanın Migration Required? bölümü buna göre güncellendi.)
