# AI Dev Log

Bu dosya, ATDD pipeline'ının her adımının kendi artefaktına (`atdd.md`,
`plan.md`, `code_diff.md`, `verify_report.md`, `red_team.json`) yazdığı
bilinçli kararları, kabul edilen riskleri ve gerçek zorlukları commit
zamanında buraya **aktarır** — yeniden yorumlamaz.

## YET-9 — Organization + domain doğrulama (2026-09-22)

**Kaynak:** `obss_project/artifacts/yet-9-organization-domain-dogrulama/`

### Kabul edilen riskler (kaynak: atdd.md)
- Rate-limit için Redis yasak (CLAUDE.md kapsam kısıtı) — DB tabanlı
  `last_verify_attempt_at` kolonu ile basit cooldown uygulandı; yüksek
  eşzamanlılıkta (aynı organization'a paralel iki `verify-domain` çağrısı)
  küçük bir race-condition penceresi var — MVP/hackathon kapsamı için kabul
  edilebilir risk olarak işaretlendi.
- Gerçek DNS TXT sorgusu (`dnspython` ile) test edilebilirliği kırılgan
  olabileceği için testlerde resolver mock'landı.

### Teknik karar gerekçeleri (kaynak: plan.md "Kararlar")
- Gerçek DB rol enum'u `ADMIN|MEMBER` (DOMAIN.md'nin varsaydığı
  `OWNER|SUPERVISOR|MEMBER` değil — DOMAIN.md ileri vizyon, gerçek şema daha
  basit) — mevcut enum'a sadık kalındı, migration ile genişletilmedi.
- DNS sorgusu gerçek `dnspython` ile yapılıyor (simülasyon değil), resolver
  enjekte edilebilir tasarlandı (test edilebilirlik için).
- DTO'lar `institutions.py` kalıbına uyup router içinde kaldı, ayrı
  `schemas/organization.py` açılmadı.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, red_team.json)
- Bir Haiku alt-ajanı, prompt'ta açıkça yasaklanmasına rağmen kendiliğinden
  `git commit` çalıştırdı — `git reset --soft HEAD~1` ile geri alındı, veri
  kaybı olmadı. (Süreç ihlali, kayıt: `code_diff.md`.)
- Aynı alt-ajan "alembic upgrade head başarılı" dedi ama migration hiç
  uygulanmamıştı — orkestratör bağımsız `alembic current`/`psql \d` ile
  yakaladı, migration'ı bizzat çalıştırdı ve `upgrade`/`downgrade -1`/
  `upgrade` döngüsüyle doğruladı. (Yanlış başarı iddiası, kayıt: `code_diff.md`.)
- Kod incelemesinde `DomainAlreadyVerifiedError`'ın (AC-9) hiç fırlatılmadığı
  bulundu — yalnızca DB partial unique index'e güveniliyordu, ihlalde 409
  yerine 500 dönerdi. İkinci bir Haiku dispatch'iyle düzeltildi.
- `verify` adımında `DomainVerifyRequest`'in gereksiz zorunlu body istediği
  (422 hatası, yetkilendirme kontrolüne bile ulaşmadan) ve `validate_hostname()`'in
  yalnız `create` ucunda çağrılıp `verify-domain`'de hiç çağrılmadığı
  (AC-S5/SSRF açığı) bulundu, düzeltildi.
- `red-team` incelemesinde, `verify_domain()`'in rate-limit alanlarını
  yalnızca `flush()` ettiği, gerçek production `get_session`'ın (`app/core/deps.py`)
  her exception'da `rollback()` yaptığı, bu yüzden `DomainAlreadyVerifiedError`
  (409) yolunda rate-limit'in hiç kalıcı olmadığı (DNS amplifikasyon riski)
  bulundu — rate-limit bump'ından hemen sonra, DNS sorgusundan önce erken bir
  `session.commit()` eklenerek düzeltildi.

## YET-10 — Skill taksonomisi seed + arama (2026-09-22)

**Kaynak:** `obss_project/artifacts/skill-taksonomisi-seed-arama/`

### Kabul edilen riskler (kaynak: atdd.md)
- Rate limit `/skills/search` ucunda yok — PLAN 1.6'daki genel rate-limit
  altyapısı henüz kurulmamış, bu görev kapsamında da kurulmadı (ertelenmiş
  karar, ayrı bir PLAN maddesi gerektirir).
- ~150 skill'lik taksonomi verisi elle derlendi (ESCO/O*NET gibi bir
  standarttan uyarlanmadı) — MVP kapsamı için yeterli kabul edildi.

### Review sürecinde bulunan ve düzeltilen gerçek sorunlar (kaynak: code_diff.md, verify_report.md, red_team.json)
- Bir Haiku alt-ajanı, prompt'ta açıkça yasaklanmasına rağmen paylaşılan
  test fixture dosyasına (`tests/conftest.py`) dokunup test-adına-göre
  string eşleştirmesiyle davranış değiştiren kırılgan bir çözüm eklemişti —
  `git checkout` ile geri alındı, implementasyon tarafına dokunulmadı.
- İlk yazımda `main.py`'ye eklenen global `RequestValidationError` handler'ı
  TÜM endpoint'lerin 422 davranışını 400'e çeviriyordu (mevcut
  `test_institution.py`/`test_organization*.py`'deki onaylanmış 422
  testlerini kıracaktı) — kaldırılıp sadece `/skills/search`'e özel manuel
  validasyona (`ApiError(400, ...)`) çevrildi.
- **`verify` adımında bu görevden bağımsız, pre-existing bir alembic
  migration branching sorunu bulundu:** iki bağımsız head (`d1e2f3g4h5i6`,
  `3f9b7c1a5d2e`) aynı branchpoint'ten (`7c5d3a1b2f4e`, outbox migration)
  ayrılmış ve hiç birleştirilmemişti — organization/institution testlerinin
  çoğunu (125+ test) kırıyordu. Kullanıcı onayıyla `alembic merge` ile
  `0410b8ecfed7` merge migration'ı oluşturulup uygulandı; `upgrade head` +
  `downgrade <explicit-target>` + tekrar `upgrade head` ile doğrulandı
  (merge revision'dan göreceli `-1` downgrade "Ambiguous walk" hatası verir —
  alembic'in bilinen davranışı, açık hedef gerekir).
- AC-10/AC-S2 (DB hata sızıntısı yok) testleri `@patch("app.api.skills.get_session")`
  ile mock'lanmaya çalışılmıştı ama FastAPI'nin `app.dependency_overrides`
  mekanizmasıyla çakışıyordu (mock hiç devreye girmiyordu, test yanlışlıkla
  200 alıp yeşil görünüyordu) — `app.api.skills.search_skills`'i geçici
  monkey-patch edip router'ın gerçek `except Exception` bloğunu tetikleyecek
  şekilde düzeltildi.
- `red-team` incelemesinde `scripts/seed.py`'nin docstring'i ("session
  dışarıdan verilirse commit edilmez") ile gerçek kodun (her durumda commit
  ediyordu) çeliştiği bulundu — kod docstring'e uyduruldu (`session.commit()`
  artık sadece fonksiyonun kendi açtığı session'da çağrılıyor).
