# Verify Report — yet-72-attestation-revoke
_Reference: atdd.md, plan.md, code_diff.md (yok — özet aşağıda), test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` ile doğrulandı |
| 2 | Build/derleme | PASS | `mypy app` başarılı |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase kullanmıyor |
| 4 | Lint (`ruff check .`) | PASS | 2 tur küçük düzeltme (kullanılmayan importlar) sonrası `All checks passed!` |
| 5 | Type check (`mypy app`) | PASS | İlk turda 2 gerçek Optional/non-Optional uyuşmazlığı bulundu (`revoked_at`/`revoke_reason`), assert ile düzeltildi |
| 6 | Unit/integration testler | PASS | `pytest tests/test_attestation_revoke.py tests/test_attestation_revoke_authorization.py -v` → 15/15 PASS (4 düzeltme turu sonrası). `pytest -q` (tam paket) → 658 passed, 4 skipped |
| 7 | E2E testler | N/A | Ayrı e2e paketi yok |
| 8 | Lighthouse | N/A | Web UI yok |
| 9 | Erişilebilirlik | N/A | Web UI yok |
| 10 | Güvenlik taraması | PASS | secrets: PASS, python_sast (bandit): PASS |
| 11 | AI code review | PENDING (red-team) | Sıradaki adım |
| 12 | Görsel regresyon | N/A | Web UI yok |
| 13 | DAST (ZAP) | N/A | Web UI yok |
| 14 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor |

## Migration Doğrulaması (2 parçalı)
- `alembic upgrade head`: PASS (`k2l3m4n5o6p7 -> l3m4n5o6p7q8`)
- `alembic downgrade -1`: PASS
- Re-`upgrade head`: PASS
- **Ortam kesintisi:** Verify sırasında Docker Desktop tamamen kapanmıştı (uzun oturum) — yeniden başlatılıp `docker compose up -d` ile DB ayağa kaldırıldı, sonra migration doğrulaması yapıldı.

## AC -> Test Mapping
| AC | Test | Sonuç |
|---|---|---|
| AC-1 (happy path + tombstone) | `TestAttestationRevokeHappyPath` (2 test) | PASS |
| AC-2 (attestor değil→403) | `TestAttestationRevokeNotAttestor` (2 test) | PASS |
| AC-3 (cross-tenant→404) | `TestAttestationRevokeScopeOut::test_revoke_cross_tenant_404` | PASS |
| AC-4 (yok→404) | `TestAttestationRevokeNotFound::test_revoke_nonexistent_attestation_404` | PASS |
| AC-5 (zaten geri çekilmiş→409) | `TestAttestationRevokeAlreadyRevoked::test_revoke_already_revoked_409` | PASS |
| AC-6 (reason boş→422) | `TestAttestationRevokeValidation` (2 test) | PASS |
| AC-7 (diğer alanlar değişmez) | `TestAttestationRevokeAppendOnly::test_revoke_preserves_original_fields` | PASS |
| AC-S1 (reason loglanmaz) | `TestAttestationRevokeAuditSecurity::test_revoke_audit_event_no_reason_text` | PASS |
| AC-S2 (race condition) | `TestAttestationRevokeRaceCondition` (2 test) | PASS |
| AC-S3 (trigger izin verilen alanlarla sınırlı) | `TestAttestationRevokeDBTrigger` (2 test) | PASS |

## Coverage / Quality Notes

**Verify sırasında bulunan ve düzeltilen sorunlar (kod incelemesiyle, orkestratör tarafından — code-copilot dispatch'inden hemen sonra, testleri çalıştırmadan ÖNCE):**

1. **Kritik güvenlik hatası (çıplak select + 403/404 sızıntısı):** İlk implementasyon `revoke_attestation()` içinde çıplak `select(Attestation)` kullanıyordu (`.claude/rules/security.md` ihlali) VE attestor olmayan HERKESE (cross-tenant dahil) `403` dönüyordu — bu, `.claude/rules/security.md`'nin "yetkisiz erişimde 404 dön, 403 değil" kuralını ve atdd.md'nin kendi AC-3'ünü ihlal ediyordu (bir attestation_id'nin geçerli olduğu, ona hiçbir ilişkisi olmayan biri tarafından bile 403 alınarak öğrenilebiliyordu). Düzeltme: attestation'ın engagement'ı önce `scoped_engagements()` ile kontrol ediliyor — scope dışıysa 404, scope içinde ama attestor değilse 403.
2. **Routing bug:** `POST /attestations/{id}/revoke` route'u yanlışlıkla `/engagements` prefix'li router'a eklenmişti, gerçek path `/engagements/attestations/{id}/revoke` oluyordu (API.md sözleşmesiyle uyuşmuyordu — plan.md bu riski zaten öngörmüştü). Ayrı bir `attestations_router` oluşturulup `main.py`'de kaydedildi.
3. **26 yerde `session.expunge_all()` test bug'ı:** Test-copilot'un yazdığı testler, mevcut proje konvansiyonunda (client/session aynı SQLAlchemy session'ı paylaşır) hiç gerekmeyen `expunge_all()` çağrıları içeriyordu — bu, sonraki `.id` erişimlerinde `DetachedInstanceError`'a yol açıyordu. Tümü kaldırıldı.
4. **Tombstone testi + AuditEvent alan adı:** Tombstone testi `skill_id` vermeden attestation oluşturuyordu (orijinal SkillSignal hiç yoktu, supersede edilecek bir şey yoktu) — düzeltildi. `AuditEvent.occurred_at` diye bir alan yok (gerçek adı `created_at`) — düzeltildi.
5. **mypy:** `revoked_at`/`revoke_reason` Optional/non-Optional uyuşmazlığı, invariant assert ile düzeltildi.

**Refactor Aday Kontrolü:** Aday yok — diff mevcut `evaluation.py`/`attestation.py` desenleriyle tutarlı, CAVEMAN'a uygun.

## Red-Team Sonrası Güncelleme (2026-09-24)
Red-team turu **approve-with-changes** verdi: `scoped_attestations()` ölü kod (silindi), bare `select()` belgelenmemişti (açıklayıcı yorum eklendi). Gate'ler tekrar çalıştırıldı:
- `ruff check .` / `mypy app` → PASS
- `pytest -q` (tam paket) → **658 passed, 4 skipped**

İkinci red-team turu: **approve**.

**Ortam notu:** `backend/.venv/Scripts/python.exe` doğrudan çağrılarak doğru proje ortamı kullanıldı (bkz. önceki görevlerin verify_report.md'lerindeki aynı not).
