# Plan — kurum-dashboard-uyeler
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/engagement.py` | `get_coordinator_dashboard()` (satır 640-733) fonksiyonuna üye sorgusu eklenecek: `InstitutionMember` sorgusu `.where(InstitutionMember.institution_id == inst_uuid)` ile (AC-1, AC-S1), dönen dict'e `"members": [...]` eklenecek. | low |
| `backend/app/api/institutions.py` | `DashboardEngagementItem`'ın yanına `DashboardMemberItem` (yeni Pydantic response şeması) eklenecek, `DashboardResponse`'a `members: list[DashboardMemberItem]` alanı eklenecek, `get_coordinator_dashboard_endpoint`'in response oluşturma satırına `members=[DashboardMemberItem(**m) for m in dashboard_data["members"]]` eklenecek. | low |
| `backend/tests/test_coordinator_dashboard.py` | Var olan dosya genişletilecek: AC-1 (happy path members), AC-2 (üye yok → boş liste, teorik), AC-S1 (çapraz-kurum: iki kurumun üyeleri karışmıyor) testleri eklenecek. | low |

## New Files
Yok — atdd.md'nin kararı gereği yeni bir uç/dosya açılmıyor, mevcutlar genişletiliyor.

## Dependencies / Kod Keşfi Sonuçları
- **`engagement.py`'de model/authorization import'u zaten var (Açık Soru ÇÖZÜLDÜ):**
  `get_coordinator_dashboard()`'ın kendi içinde (satır 681-682) zaten
  `from app.models import Institution` ve `from app.services.authorization import
  scoped_institutions` yapılıyor — yani bu dosyanın `models`/`authorization`'dan içe aktarma
  yapması ZATEN kurulu bir precedent. `InstitutionMember`'ı aynı şekilde (fonksiyon içinde veya
  dosya başında, mevcut `Engagement, Organization, TalentProfile, Skill, SkillSignal` import
  satırına eklenerek) içe aktarmak mimari kurala aykırı DEĞİL.
- **Test kırılma riski ÇÖZÜLDÜ (atdd.md'nin Risks bölümü doğrulandı):** `test_coordinator_dashboard.py`
  hiçbir yerde `assert response.json() == {...tam sözlük...}` yapmıyor — hep `"key" in data` (varlık)
  ve tekil alan (`data["institution_id"] == ...`) kontrolü var (satır 406-418 örnek). Yeni `members`
  alanı eklenmesi HİÇBİR mevcut testi kırmaz.
- `InstitutionMember(id, institution_id, user_id, role)` — `role` CHECK constraint zaten yalnız
  `'ADMIN'`/`'COORDINATOR'` kabul ediyor, ek bir filtre gerekmiyor (tablo zaten bu iki değere
  sınırlı). `TimestampMixin`'den `created_at` var, `joined_at` olarak kullanılacak.
- `User(id, email, ...)` — isim alanı yok, `email` tek insan-okunabilir alan (atdd.md'de zaten
  not edildi).
- Mevcut `DashboardEngagementItem`/`DashboardSummary` deseni: düz Pydantic `BaseModel`, ORM'den
  ayrı — `DashboardMemberItem` aynı deseni izleyecek.

## Migration Required?
**Hayır.** `InstitutionMember` ve `User` tabloları zaten var, yeni kolon/tablo gerekmiyor —
sadece mevcut verinin okunup response'a eklenmesi.

## Risks
(atdd.md'den taşındı, ikisi de bu plan aşamasında ÇÖZÜLDÜ — artık risk değil, bilgi amaçlı)
- ~~Mevcut testler kırılabilir~~ → ÇÖZÜLDÜ, kırılmıyor (yukarıda kanıtlandı).
- ~~`engagement.py`'nin import'u mimari kurala aykırı olabilir~~ → ÇÖZÜLDÜ, zaten precedent var.
- (Kalan, atdd.md'den) Sayfalama yok — bilinçli kabul edilen risk, bu planı etkilemiyor.

## Open Questions
Yok — atdd.md'nin bıraktığı tek açık soru (üye sorgusunun nereye ekleneceği) kod keşfiyle
kesinleşti: `engagement.py::get_coordinator_dashboard()` içine, mevcut precedent'e uygun şekilde.
Sonnet 5 alt-ajanına yönlendirilecek soru yok.
