# Test Diff — guv-02-davet-yaniti-duzeltmesi

## Genişletilen dosyalar
- `backend/tests/authorization/test_organization_authorization.py` (+329 satır) — yeni sınıf `TestInviteOrganizationMember`, 6 test.
- `backend/tests/authorization/test_institution_authorization.py` (+500 satır) — yeni sınıf `TestInviteInstitutionMember`, 9 test.

Tüm fixture'lar (`user_a_admin`, `user_a_member`, `user_a_coordinator`, `user_b_admin`, `user_to_invite`, `org_a_admin_member`, `org_a_member`, `org_b_admin_member`, `inst_a_admin_member`, `inst_a_coordinator_member`, `inst_b_admin_member`, `organization_a/b`, `institution_a/b`) dosyalarda ZATEN vardı — hiçbiri yeniden icat edilmedi, `Read` ile doğrulandı.

## AC Eşlemesi
| AC | Test Fonksiyonu | Dosya |
|---|---|---|
| AC-1 (happy path) | `test_invite_known_user_valid_role_202_queued` | org |
| AC-1 (happy path + audit) | `test_invite_known_user_valid_role_202_queued_with_audit` | institution |
| AC-2 (bilinmeyen e-posta) | `test_invite_unknown_email_202_no_membership_created` | org |
| AC-2 (bilinmeyen e-posta + audit) | `test_invite_unknown_email_202_no_membership_with_audit` | institution |
| AC-3 (geçersiz rol) | `test_invite_invalid_role_422_invalid_role_code` | org + institution |
| AC-4 (zaten üye, rol değişmez) | `test_invite_already_member_202_role_unchanged` | org + institution |
| AC-5 (son ADMIN korunur) | `test_single_admin_re_invite_role_unchanged_protects_admin_count` | institution |
| AC-6 (audit event) | `test_invite_success_audit_event_created`, `test_invite_unknown_email_audit_event_created_without_pii` | institution |
| AC-7 / AC-S1 (çapraz-kiracı, org) | `test_cross_tenant_org_b_admin_cannot_invite_to_org_a_404`, `test_member_cannot_invite_404` | org |
| AC-8 / AC-S5 (çapraz-kiracı + COORDINATOR, institution) | `test_cross_tenant_inst_b_admin_cannot_invite_to_inst_a_404`, `test_coordinator_cannot_invite_404` | institution |

## Bağımsız doğrulama (orkestratör tarafından, sub-agent'ın kendi raporuna güvenilmeden)
- `git status --short` ile her iki dosyanın gerçekten değiştiği doğrulandı.
- `git diff` ile testlerin içeriği satır satır okundu: tam eşleşme assertion'ları (`== 202`, `== {"status": "queued"}`, `.get("code") == "INVALID_ROLE"`) kullanılmış, gevşek `in`/`.lower()` yok.
- "Zaten üye"/"son ADMIN" testleri DB'den davet ÖNCESİ ve SONRASI rolü ayrıca okuyup karşılaştırıyor (sadece HTTP yanıtına bakmıyor) — atdd.md'nin "yazma testinde son durumu doğrula" kuralı karşılanmış.
- **Kritik bir çelişki bulundu ve `plan.md`'de düzeltildi (code-copilot'tan ÖNCE):** `app/main.py`'deki Pydantic `RequestValidationError` handler'ı `code: "VALIDATION_ERROR"` üretiyor, `ApiError`/manuel `HTTPException` handler'ı ise `exc.detail`'deki kodu aynen geçiriyor. Eğer code-copilot rol validasyonunu Pydantic `Literal`'a taşırsa testler (`INVALID_ROLE` bekliyor) YANLIŞLIKLA fail eder. `plan.md`'ye not düşüldü: rol validasyonu Pydantic Literal'a DEĞİL, organizations.py'nin zaten yaptığı gibi handler içinde elle (`if role not in (...): raise ApiError(422, "INVALID_ROLE", ...)`) yapılmalı.

## Kapsanmayan (bilinçli, sub-agent'ın raporunda belirtildi)
- Davranış Sözleşmesi satır 8 (kısmi başarı: üyelik yazıldı, outbox enqueue aynı tx'te başarısız) — ayrı bir entegrasyon testi gerektirir, bu turda yazılmadı. `verify` aşamasında not düşülecek, gerekirse ayrı bir `test-copilot` turu istenebilir.
- Kimliksiz istek → 401 — mevcut auth dependency zaten test edilmiş bir davranış, tekrar yazılmadı.

## AuditEvent action isim varsayımı
Sub-agent `"INVITE_INSTITUTION_MEMBER"` action ismini varsaydı (org'daki `"INVITE_ORG_MEMBER"` deseniyle tutarlı). code-copilot bu ismi kullanmalı, aksi halde testler fail eder — bu, code-copilot'un dispatch prompt'una açıkça yazılacak.
