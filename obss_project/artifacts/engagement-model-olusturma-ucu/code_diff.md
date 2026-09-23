# Code Diff — engagement-model-olusturma-ucu

## Oluşturulan Dosyalar
- `backend/alembic/versions/g8h9i0j1k2l3_add_engagements_table.py` — `engagements` tablosu, 3 CHECK kısıtı, 4 index (indexler doğrulandı: organization_id+status, talent_id+status, institution_id+status, partial status=PENDING_EVALUATION), 4 FK. `alembic upgrade head` ve tablonun oluşumu doğrulandı.
- `backend/app/models/engagement.py` — `Engagement` ORM modeli (Base + TimestampMixin, aynı CHECK'ler ORM tarafında da tekrarlanmış).
- `backend/app/services/engagement.py` — `create_engagement()`: sahiplik kontrolü (TALENT/ORG_MEMBER/ORG_ADMIN dışı roller default-deny ile 404), talent/org/institution varlık ve eşleşme kontrolleri, `log_audit_event` ile aynı transaction'da audit kaydı (title/description audit metadata'sına konulmuyor).
- `backend/app/api/engagements.py` — `POST /engagements`, Pydantic DTO'lar (`kind` alanı `Literal[...]` ile CHECK kümesiyle eşleşiyor, `title` `min_length=1`), hata gövdesi `{code, message, request_id}` deseni.

## Değiştirilen Dosyalar
- `backend/app/models/__init__.py` — `Engagement` export edildi.
- `backend/app/services/authorization.py` — SADECE `scoped_engagements()` eklendi (TALENT→talent_id, ORG_MEMBER/ORG_ADMIN→org_ids, COORDINATOR/INST_ADMIN→institution_ids, aksi halde boş sonuç). Var olan fonksiyonlara dokunulmadı.
- `backend/app/main.py` — `engagements_router` include edildi.

## Code-copilot sonrası bulunan ve düzeltilen 3 gerçek hata (ilk teslimde YOKTU, review'da bulundu)
1. **AC-2 kırığı**: `kind` alanı düz `str` idi, geçersiz değer Pydantic'i geçip yakalanmamış `IntegrityError` olarak sızıyordu (500). `Literal[...]` ile düzeltildi.
2. **Ölü kod**: `engagement.py`'de asla çalışamayacak bir `elif` dalı vardı, silindi.
3. **Kritik güvenlik açığı (default-allow)**: `principal.kind` TALENT/ORG_MEMBER/ORG_ADMIN dışındaysa (ör. "USER", "COORDINATOR") hiçbir sahiplik kontrolü uygulanmıyordu — herhangi bir authenticated kullanıcı herhangi bir organizasyon adına engagement açabiliyordu. Fonksiyon başına default-deny kontrolü eklendi.
4. **Validasyon eksik**: `title=""` 422 yerine 201 dönüyordu, `min_length=1` eklendi.

Ayrıca test-copilot'un yazdığı fixture'larda 2 hata bulunup düzeltildi (kod değil, test tarafı): `Organization`/`Institution` fixture'ları var olmayan alanlar (`slug`, `visibility`, `logo_url`, `website`) kullanıyordu; `user_org_member_charlie` fixture'ında gerçek bir `OrganizationMember` satırı eksikti (AC-S2 testi yanlış senaryoyu test ediyordu).

## Doğrulanan test sonucu (2026-09-23)
```
tests/test_engagement.py + tests/test_engagement_authorization.py + tests/authorization/test_matrix.py:
56 passed, 4 skipped

tests/authorization (tam paket):
73 passed, 4 skipped
```
Regresyon yok. 4 skip = Faz 2'nin henüz yazılmamış diğer parçaları (Evidence/Evaluation/Attestation), kapsam dışı.

## Bilinen sınırlama (verify/red-team'e taşınan not)
`test_diff.md`'de belirtildiği gibi `test_engagement_access_org_member_read_own_org`
ve `test_coordinator_scope_filtering` testleri pozitif doğrulama (en az 1 doğru
kiracıya ait kayıt döndüğü) yapmıyor, sadece negatif doğrulama (yanlış kiracıya
ait kayıt yoksa) yapıyor — boş sonuç da testi geçer. `scoped_engagements()`
davranışı bu yüzden CI'da tam güvenceli değil.
