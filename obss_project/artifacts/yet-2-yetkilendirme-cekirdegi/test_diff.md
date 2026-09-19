# Test Diff — yet-2-yetkilendirme-cekirdegi (red step)

## Oluşturulan dosyalar
- `backend/tests/test_authorization.py` (566 satır, 22 test fonksiyonu)
- `backend/tests/test_audit_events.py` (511 satır, 21 test fonksiyonu, 2 düzeltme turu sonrası)

## AC → Test eşlemesi
| AC | Test fonksiyonu/fonksiyonları |
|---|---|
| AC-1 | `test_principal_accepts_all_kind_values_*` (9 fonksiyon, her Principal.kind için biri) |
| AC-2 | `test_scoped_organizations_returns_select_object`, `test_scoped_talent_profiles_returns_select_object` |
| AC-3 | `test_can_true_for_own_resource`, `test_can_false_for_others_resource` |
| AC-4 | `test_log_audit_event_inserts_row`, `test_log_audit_event_with_ip_address`, `test_log_audit_event_result_denied`, `test_log_audit_event_result_error`, `test_log_audit_event_invalid_result_raises_integrity_error`, `test_log_audit_event_with_metadata` |
| AC-5 | `test_get_scoped_or_404_returns_none_when_empty` |
| AC-S1 | `test_can_default_deny_undefined_action` (parametrized, 9 kind) |
| AC-S2 | `test_scoped_organizations_tenant_isolation`, `test_scoped_talent_profiles_tenant_isolation` |
| AC-S3 | `test_audit_event_update_blocked_by_trigger_orm`, `test_audit_event_delete_blocked_by_trigger_orm`, `test_audit_event_update_blocked_by_trigger_raw_sql`, `test_audit_event_delete_blocked_by_trigger_raw_sql` |
| AC-S4 | `test_get_scoped_or_404_out_of_scope_returns_none`, `test_get_scoped_or_404_nonexistent_returns_none`, `test_get_scoped_or_404_out_of_scope_and_nonexistent_same_result` |
| AC-S5 | `test_can_defense_in_depth_checks_ownership`, `test_can_ownership_check_independent_of_scoped` |
| AC-S6 | `test_log_audit_event_rejects_password_in_metadata`, `_password_hash_`, `_email_`, `_tc_kimlik_no_`, `test_log_audit_event_accepts_safe_metadata`, `_rejects_multiple_sensitive_keys`, `_nested_metadata_with_sensitive_keys`, `_case_insensitive_pii_check` |
| (ek) | `test_audit_events_table_exists`, `test_audit_events_has_required_columns`, `test_audit_events_result_check_constraint` — tablo/kolon/CHECK varlığı |

## İlk turda bulunan ve düzeltilen 2 hata (implementasyon yazılmadan önce fark edildi)
1. **`session.execute(session.query(AuditEvent).filter_by(...))`** — SQLAlchemy 1.x `Query` nesnesi 2.0 `execute()`'a veriliyordu, geçersiz API karışımı, runtime hatası verirdi. 10 yerde `select(AuditEvent).filter_by(...)`'e çevrildi.
2. **`audit_row.metadata`** — SQLAlchemy'de `metadata` `DeclarativeBase` üzerinde rezerve bir isim (`InvalidRequestError` fırlatır). Karar: DB kolonu `metadata` kalır (docs/DATABASE.md'ye uyum), Python/ORM attribute adı `event_metadata` olur (`mapped_column("metadata", ...)` ile eşlenecek — bu karar code-copilot'a aktarılmalı). 4 yerde `audit_row.event_metadata`'ya çevrildi. `log_audit_event()`'in `metadata=` kwarg'ı ve raw SQL/information_schema referansları (gerçek DB kolon adı) DEĞİŞMEDİ.

## Bilinen zayıf testler (red-team'e not — bu aşamada düzeltilmedi, kapsam/zaman dengesi)
- `test_scoped_talent_profiles_tenant_isolation`: docstring'i "AC-S2 tenant izolasyonu" diyor ama yorum satırında "profile2 may or may not be returned... simplified test" diyerek gerçek bir izolasyon iddiası yapmıyor — AC-S2'nin talent_profiles tarafı institution_id bazlı gerçek bir karşı-örnek (Institution A/B) içermiyor, sadece `organizations` tarafı (org_a/org_b) gerçek izolasyon test ediyor.
- `test_get_scoped_or_404_out_of_scope_and_nonexistent_same_result`: aynı `scoped_select` nesnesini iki kez çalıştırıyor, "kapsam dışı" ile "gerçekten yok" senaryolarını ayrı veri kurulumlarıyla değil aynı sorguyla simüle ediyor — AC-S4'ün iddiasını zayıf kanıtlıyor.

Bu iki zayıflık `code-copilot`'un implementasyonunu engellemez (testler yine de anlamlı davranış zorunlu kılıyor), ama `red-team`'in test-gap kategorisinde işaretlemesi beklenir.

## Beklenen durum
Bu testler şu an **RED** (başarısız) — `backend/app/services/authorization.py`, `backend/app/services/audit.py`, `backend/app/models/audit.py` henüz yok (`ModuleNotFoundError`). Bu beklenen ve doğru bir durumdur (TDD red step). `code-copilot` bu testleri GREEN yapacak implementasyonu yazacak, test dosyalarına dokunmayacak.
