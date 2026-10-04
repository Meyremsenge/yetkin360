# Plan — calismalar-gercek-backend-baglama
_Reference: atdd.md_

Frontend-pipeline: tetikleyici YOK — sadece `.ts` veri katmanı dosyaları
değişiyor (`engagements.ts`), hiçbir `.tsx`/JSX render kodu değişmiyor,
atdd.md "Görsel/UI kriteri: Yok" diyor.

## Kod keşfi (mevcut kalıplar)
- `scoped_engagements(session, principal)` (`app/services/authorization.py:187`)
  zaten tenant izolasyonunu satır bazında yapıyor — hem liste hem detay bunu
  kullanacak.
- Detay/tekil kayıt lookup kalıbı proje genelinde AYNI: `get_scoped_or_404(
  scoped_engagements(session, principal).where(Engagement.id == engagement_uuid),
  session)` (`transition_engagement`, `create_engagement_task`,
  `create_deliverable` hepsi bunu kullanıyor — `engagement.py:249-251` vb.).
- `Organization`, `Deliverable`, `EngagementTask` zaten `engagement.py`'de
  import edilmiş durumda.
- Yetkilendirme test dosyası (`test_engagement_authorization.py`) zaten
  `TestTalentUnauthorizedAccess`/`TestOrgMemberUnauthorizedAccess`/
  `TestInstitutionMessagePrivacy` gibi sınıflarla organize — yeni liste/detay
  testleri aynı yapıya eklenecek.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/services/engagement.py` | `list_engagements()` ve `get_engagement_detail()` servis fonksiyonları eklenir (AC-1..8) | medium (JOIN + iki alt-sorgu) |
| `backend/app/api/engagements.py` | `GET /engagements` ve `GET /engagements/{id}` endpoint'leri eklenir (AC-1..8, AC-S1/AC-S2) | low (mevcut router'a ekleme) |
| `backend/tests/authorization/test_engagement_authorization.py` | Liste/detay için pozitif + negatif (404) yetkilendirme testleri eklenir | low |
| `frontend/lib/api/engagements.ts` | `USE_MOCK_LIST`/`USE_MOCK_DETAIL` ve mock store kodu (seedEngagements/loadStore/saveStore/findInStore) SİLİNİR, `listEngagements`/`getEngagement` doğrudan `apiFetch` kullanır (AC-9) | medium (mevcut `transitionEngagement`'ın mock dallanması da mock store'a bağlı — dikkatle ayrıştırılmalı) |
| `frontend/lib/api/engagements.test.ts` | Mock-store testleri kaldırılır, gerçek `apiFetch` mock'landığı testlerle değiştirilir | medium |

## New Files
Yok.

## Dependencies
- `Organization.name` → JOIN ile `organization_name` alanına eşlenecek.
- `EngagementTask`/`Deliverable` → `engagement_id` ile ayrı sorgu (detay
  ucunda), N+1'den kaçınmak için TEK sorgu (`WHERE engagement_id = :id`,
  liste ucu için sorun yok çünkü sadece detay ucu bunları içeriyor).
- `frontend/lib/api/engagements.ts`'teki `transitionEngagement()` fonksiyonu
  ZATEN gerçek uca gidiyordu (`POST /engagements/{id}/transitions`) — SADECE
  mock ID'ler için özel dallanması vardı (`if (!mock || !store)`). Mock store
  tamamen silinince bu fonksiyon SADELEŞİR (her zaman gerçek uca gider),
  `availableTransitions()`/`isReasonRequired()` fonksiyonları DEĞİŞMEDEN kalır.

## Migration Required?
Hayır — hiçbir yeni tablo/kolon gerekmiyor, mevcut `Engagement`/`Organization`/
`EngagementTask`/`Deliverable` tabloları yeterli.

## Risks
- (atdd.md'den taşındı) Frontend/backend response şema uyuşmazlığı riski —
  Davranış Sözleşmesi'ndeki JSON örnekleri birebir kullanılacak.
- (atdd.md'den taşındı) `lib/api/engagements.test.ts`'in mock-state-machine
  testleri (`transitionEngagement`) DEĞİŞMEDEN kalabilir çünkü zaten gerçek
  uca gidiyordu — sadece list/detail mock'ları siliniyor.
- **Yeni risk:** `EngagementTask.due_at`/`completed_at` ve `Deliverable`'ın
  diğer alanları (`skill_id`, `description`) frontend'in beklediği
  `EngagementTask {id, title, status}`/`EngagementDeliverable {id, title,
  submitted_at}` tiplerinden DAHA GENİŞ — backend response'u sadece
  frontend'in beklediği alt-kümeyi döndürmeli (frontend tipini genişletmeye
  gerek yok, atdd.md'nin JSON örnekleri zaten dar).

## Open Questions
Yok.
