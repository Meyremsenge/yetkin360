# Test Diff — a01-giris-kilitleme
_Reference: atdd.md, plan.md_

## Oluşturulan / Genişletilen Dosyalar

### Genişletildi: `backend/tests/authorization/test_auth_endpoints.py`
`TestLogin` sınıfına 9 yeni test metodu eklendi (4 mevcut test dokunulmadan
korundu). Bu dosya `session`/`client` fixture'larını (savepoint-mode, flush
görünür) kullanır.

**Not (kalite kontrolü):** İlk dispatch'te Haiku alt-ajanı bu 9 metodu
yanlışlıkla iki kez eklemişti — biri `TestLogin` içinde doğru, biri
`TestRefresh`'ten hemen önce class gövdesi dışında (sözdizimi hatası
üretecek şekilde). İkinci dispatch ile düzeltildi; `python -m ast.parse` ile
sözdizimi ve `pytest --collect-only` ile 42 testin (4 var olan TestLogin +
9 yeni TestLogin + var olan diğer tüm sınıflar + 4 yeni real-session) hatasız
toplandığı doğrulandı.

### Yeni dosya: `backend/tests/authorization/test_auth_login_real_session.py`
`test_auth_refresh_real_session.py`'nin desenini birebir takip eder: ayrı
`create_engine`/`sessionmaker`, `TestClient(app)` **override'sız** (gerçek
`get_session`, gerçek commit/rollback), `finally` bloğunda temizlik.

## Acceptance Criteria Eşlemesi

| AC | Test dosyası | Test fonksiyonu |
|---|---|---|
| AC-1 | test_auth_login_real_session.py | `test_login_wrong_password_persists_failed_login_count_through_real_commit_rollback` |
| AC-2 | test_auth_endpoints.py | `test_login_tenth_failed_attempt_returns_401_and_sets_lock_until`, `test_login_after_lock_returns_423_with_account_locked` |
| AC-2 (real) | test_auth_login_real_session.py | `test_login_tenth_wrong_password_locks_account_persisted_in_real_db` |
| AC-3 | test_auth_endpoints.py | `test_login_wrong_password_logs_audit_denied` |
| AC-3 (real) | test_auth_login_real_session.py | `test_login_wrong_password_logs_audit_event_that_survives_rollback` |
| AC-4 | test_auth_endpoints.py | `test_login_expired_lock_with_correct_password_succeeds_and_resets_count` |
| AC-5 | test_auth_endpoints.py | `test_login_suspended_user_with_correct_password_returns_invalid_credentials` |
| AC-6 | test_auth_endpoints.py (mevcut, değişmedi) | `test_login_success_sets_httponly_cookies_not_body` |
| AC-7 | test_auth_endpoints.py | `test_login_refresh_token_denied_for_suspended_user` |
| AC-8 | test_auth_endpoints.py | `test_login_expired_lock_with_wrong_password_resets_count_and_increments_by_one` |
| AC-9 (rollback semantiği) | test_auth_login_real_session.py | tüm 4 test (override'sız gerçek session kullanıyor) |
| AC-S1 (audit PII guard) | test_auth_endpoints.py | `test_login_locked_account_audit_contains_only_locked_reason` |
| AC-S1 (real) | test_auth_login_real_session.py | `test_login_locked_account_audit_metadata_clean_no_pii` |
| AC-S2 (numaralandırma) | test_auth_endpoints.py | `test_login_suspended_vs_wrong_password_same_response_enumeration_protection` |

## Beklenen Durum
Implementasyon (`backend/app/services/auth.py`) henüz DEĞİŞMEDİ — bu testler
şu an **red** (başarısız) olmalı. `code-copilot` adımı bu testleri yeşile
çevirecek implementasyonu yazacak.

## Doğrulama (bu adımda yapılan)
- `python -c "import ast; ast.parse(...)"` → sözdizimi geçerli.
- `pytest --collect-only -q` → 42 test hatasız toplandı, tekrar yok.
- Testler ÇALIŞTIRILMADI (implementasyon yok; çalıştırma `verify` adımının
  işi).
