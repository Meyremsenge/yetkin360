# Test Diff — public-dogrulama-linki (red step)

## Oluşturulan Dosyalar
- `backend/tests/test_public_verification.py` (630 satır) — functional/integration testleri
- `backend/tests/authorization/test_public_verification_authz.py` (730 satır) — güvenlik/enumeration testleri

## AC → Test Eşlemesi
| AC | Test | Dosya |
|---|---|---|
| AC-1 | `TestAC1HappyPath` (2 test) | test_public_verification.py |
| AC-2 | `TestAC2TokenNotFound` (3 test) | test_public_verification.py |
| AC-3 (AC-S2) | `TestAC3EnumerationProtection`, `TestSecurityMatrixRows1to4AllIdentical` (8 test) | authz dosyası |
| AC-4 (AC-S1) | `TestSecurityMatrixRow6TokenEntropy` — **placeholder**, implementasyon sonrası doldurulacak | authz dosyası |
| AC-5 (AC-S4) | `TestAC5S4NoPIIFields`, `TestSecurityMatrixRow5PublicVisibility` (8 test) | her ikisi |
| AC-6 | `TestAC6SnapshotSemantics` | test_public_verification.py |
| AC-7 | `TestAC7DBError` — **placeholder** (DB error injection implementasyon sonrası) | test_public_verification.py |
| Auth-free | `TestAuthFreeAccess*` (4 test) | her ikisi |

## Kritik doğrulama
Güvenlik matrisi satır 1-4 (var olmayan token, PRIVATE, INSTITUTION, ORGANIZATIONS) için `code`+`message` alanlarının tam eşitliği (`request_id` hariç, her istekte farklı UUID) — `TestSecurityMatrixRows1to4AllIdentical`.

## Düzeltildi — fixture'lar gerçek public_token kullanıyor
İlk turda fixture'lar `public_token` satırlarını yorum satırına almıştı (migration henüz yokken). Migration uygulandıktan sonra ayrı bir test-copilot turuyla düzeltildi: 5 fixture'a benzersiz gerçek `public_token` değerleri verildi, 9 test sabit `"placeholder_public_token"` yerine fixture'ın gerçek `.public_token` alanını okuyacak şekilde güncellendi. AC-2/Security Matrix Row 1 (var olmayan token) testleri zaten doğruydu, dokunulmadı.

## Durum
RED (beklenen) — migration uygulandı (DB'de kolon var), testler doğru fixture'larla kurulu, ama servis+endpoint implementasyonu henüz yok. Sonraki adım: servis+endpoint implementasyonu (code-copilot, Tur 2).
