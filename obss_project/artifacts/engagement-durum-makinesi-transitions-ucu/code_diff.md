# Code Diff — engagement-durum-makinesi-transitions-ucu

## Değiştirilen Dosyalar (yeni dosya yok)
- `backend/app/services/engagement.py` — 5 yeni domain exception (`EngagementNotFoundError`, `IllegalTransitionError`, `PreconditionFailedError`, `TransitionForbiddenError`, `VersionConflictError`), `transition_engagement()` fonksiyonu (transition_table: T1/T2/T3/T6, ön koşul kontrolü, yetki kontrolü, ham `UPDATE ... WHERE status=... AND version=...` ile optimistic locking, aynı transaction'da AuditEvent + outbox). `TransitionSpec` TypedDict (mypy type-safety için).
- `backend/app/api/engagements.py` — `TransitionEngagementRequest` DTO, `POST /{engagement_id}/transitions` route (5 exception → HTTP kodu eşlemesi), `PostEngagementResponse`'a `updated_at` alanı eklendi (hem create hem transition için).

## Code-copilot sonrası bulunan ve düzeltilen sorunlar
1. **Response şema eksikliği**: `PostEngagementResponse`'da `updated_at` alanı yoktu — testler bunu bekliyordu (atdd.md happy-path örneğinde vardı). Eklendi.
2. **mypy tip hatası**: `transition_table` dict'i karışık tipli değerler (list + callable) içerdiği için mypy değer tipini `object` olarak çıkarsıyordu (`preconditions` iterate edilemiyor, `can_transition` çağrılamıyor hatası). `TransitionSpec` TypedDict eklenerek düzeltildi.
3. **Test dosyasında 2 gerçek hata bulundu** (implementasyon değil, test-copilot'un ilk teslimi): (a) 5 test fonksiyonu `user_inst_coord_diana`/`user_org_admin_evan` (sadece User, üyelik satırı yok) fixture'ını istiyordu, gerçek üyelik satırını oluşturan `inst_coord_diana`/`org_admin_evan` fixture'ını HİÇ istemiyordu — bu yüzden principal.kind "COORDINATOR"/"ORG_ADMIN" yerine "USER" oluyordu, 404 alıyorlardı; (b) bir testte yanlış kullanıcı-engagement eşleşmesi vardı (`user_talent_alice` header'da ama engagement `talent_charlie_no_institution`'a ait). İkisi de test dosyasında düzeltildi.
4. **Önceki teslimde var olmayan `InstitutionCoordinator` modeli** import edilmişti (test-copilot'un ilk teslimi, code-copilot'tan ÖNCE bulundu) — gerçek model `InstitutionMember(role="COORDINATOR")` ile değiştirildi.

## Doğrulanan test sonucu (2026-09-23)
```
tests/test_engagement_transitions.py + test_engagement.py + test_engagement_authorization.py + test_matrix.py:
73 passed, 4 skipped

pytest -q (tam proje):
379 passed, 4 skipped (öncekinden +17, regresyon yok)

ruff check .: All checks passed!
mypy app: Success: no issues found in 42 source files
```

## Red-team sonrası düzeltmeler (2026-09-23)
1. **[high/security] Scope genişlemesi düzeltildi**: `INST_ADMIN` rolü T2/T3/T6'dan tamamen kaldırıldı (atdd.md'nin persona tanımı hiç INST_ADMIN içermiyordu; kod yanlışlıkla eklemiş, üstelik yanlış scope listesiyle — `institution_ids` yerine `institution_admin_ids` olmalıydı). Artık sadece `COORDINATOR` yetkili (T2/T3), `ORG_ADMIN`/`COORDINATOR` (T6).
2. **[medium/correctness] `reason` kalıcılığı eklendi**: Yeni migration `h9i0j1k2l3m4_add_engagement_reason_column` (`engagements.reason`, nullable Text). T3/T6 başarılı olduğunda `reason` engagement satırına yazılır (T1/T2'de `reason=None` geldiğinde mevcut değer korunur, sıfırlanmaz). AC-15 olarak atdd.md'ye eklendi, `TestTransitionReasonPersistence` (2 test) ile doğrulandı.

## Bilinen gözlem (red-team'e not — engellemeyen bir tasarım kararı)
`transition_engagement()`'ta version kontrolü, transition tablosu/ön koşul/yetki
kontrollerinden ÖNCE yapılıyor (atdd.md'nin Davranış Sözleşmesi'nde önerilen
sıra: 404→422 ILLEGAL→422 PRECONDITION→403→409). Bu sıra STATE_MACHINE.md'de
açıkça zorunlu kılınmamış (sadece 5 farklı kod olması gerektiği söyleniyor,
sıra değil) ve AC-S1/AC-S4'ün "version tampering'e karşı erken savunma"
gerekçesiyle tutarlı — ama farklı bir istemci senaryosunda (ör. hem version
eski HEM yetkisiz) kullanıcıya "409 CONFLICT" yerine "403 FORBIDDEN" görmesi
daha öğretici olabilirdi. Davranışsal bir hata değil, red-team'in
değerlendirmesine bırakıldı.
