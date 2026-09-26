# Code Diff — yet-108-toplu-hatirlatma-ucu
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `backend/app/schemas/reminder.py` — `ReminderCreate` (`engagement_ids: list[UUID]` min_length=1, `template: str` min_length=1), `ReminderResponse` (`queued_count: int` ge=0).
- `backend/app/services/reminder.py` — `create_reminders()`: `scoped_engagements()` ile institution-scope filtreleme, geçerli her engagement için `Outbox(topic=f"reminder.{template}", ...)`, `queued_count > 0` ise `log_audit_event()` (plan.md'nin önerdiği PII-guard'lı yardımcı, `AuditEvent` doğrudan inşa edilmemiş — doğru).

## Değiştirilen Dosyalar
- `backend/app/api/institutions.py` — `POST /{institution_id}/reminders` route'u eklendi (satır 310-389). `invite_member_endpoint` pattern'i izlenmiş: `institution_id not in principal.institution_ids` → 404, ardından defense-in-depth `scoped_institutions()` + `get_scoped_or_404()` → 404. Diğer route'lara dokunulmamış.

## Bulunan ve Düzeltilen Hata (code-copilot review sırasında)
`atdd.md`'nin ilk halinde AC-2/AC-7 için "`400` döner" yazıyordu — bu **benim ATDD aşamasındaki
hatamdı**, projenin gerçek davranışını kontrol etmemiştim. Gerçek kod (`backend/app/main.py:56-72`,
`RequestValidationError` handler'ı) Pydantic şema hatalarında **`422`** dönüyor, `test_talent.py`/
`test_organization.py`'deki mevcut testler de bunu doğruluyor (`400` bu projede yalnız elle
fırlatılan iş-kuralı hataları için kullanılıyor, ör. `verify-domain`'in free-email-domain reddi).

İmplementasyon (Pydantic `Field(min_length=1)`) baştan doğruydu — sorun yalnız test-copilot'un
yazdığı 4 assertion'daydı (`test_empty_engagement_ids_400`, `test_missing_engagement_ids_field_400`,
`test_empty_template_400`, `test_missing_template_400`, hepsi `== 400` bekliyordu). Düzeltme:
1. `atdd.md`: AC-2, AC-7 ve Davranış Sözleşmesi satır 2 → `422` olarak güncellendi, düzeltme notu eklendi.
2. `backend/tests/test_reminders.py`: 4 fonksiyon `422` bekleyecek şekilde düzeltildi (ve okunabilirlik
   için adları `..._422` olarak yeniden adlandırıldı) — ayrı bir Haiku alt-ajanı dispatch edilerek
   yapıldı (kod/test dosyalarını orkestratör doğrudan Edit etmiyor kuralı korundu).

## AC Karşılanması (Read ile doğrulandı, alt-ajan özetine güvenilmedi)
| AC | Karşılandı mı | Not |
|---|---|---|
| AC-1 (happy path) | ✅ | `Outbox` + `log_audit_event()` tek transaction'da (`session.flush()` route'ta) |
| AC-2 (boş/eksik engagement_ids) | ✅ (düzeltme sonrası) | Pydantic → 422 |
| AC-3 (cross-institution kısmi başarı) | ✅ | `scoped_engagements()` + `institution_id` filtresi |
| AC-4 (cross-tenant path → 404) | ✅ | `institution_id not in principal.institution_ids` |
| AC-5 (yetkisiz rol → 404) | ✅ | `institution_ids` yalnız `InstitutionMember`'dan geliyor (deps.py doğrulandı) — TALENT/ORG_MEMBER için boş liste |
| AC-6 (tümü filtrelendi → 202/0) | ✅ | `queued_count > 0` kontrolüyle audit_event de atlanıyor (test_diff.md'nin işaret ettiği boşluk kapandı) |
| AC-7 (geçersiz template) | ✅ (düzeltme sonrası) | Pydantic → 422 |
| AC-S1/S2 (cross-tenant/rol yükseltme → 404) | ✅ | Aynı authorization check |
| AC-S3 (id enumeration — queued_count sızıntısı yok) | ✅ | Response yalnız `queued_count` döndürüyor, filtrelenen id'ler response'ta yok |
| AC-S6 (audit'te PII yok) | ✅ | `log_audit_event()`'in otomatik PII guard'ı (email/password/tc_kimlik_no anahtarları) |

## Kalan Küçük Not (engelleyici değil)
`services/reminder.py` satır 58'de `Engagement.id.in_(engagement_ids) if engagement_ids else False`
— `engagement_ids` Pydantic tarafından zaten min_length=1 ile garanti edildiği için `else False` dalı
şu an ulaşılamaz kod. Zararsız ama CAVEMAN "dead code yok" ilkesine küçük bir istisna. `refactor`
aşamasında temizlenebilir, `verify`'ı bloklamıyor.

## CAVEMAN Değerlendirmesi
Yeni soyutlama yok, yardımcı fonksiyon yok (doğrudan `scoped_engagements`, `Outbox`, `log_audit_event`
kullanılmış). Kapsam dışı hiçbir şey (throttle/dedup/cap) eklenmemiş.

## Sıradaki Adım
`verify` — testleri gerçekten çalıştırma + lint/mypy + `pytest tests/authorization -q` tamamı
(CLAUDE.md kuralı: yetkilendirme değişikliğinde tam paket zorunlu).
