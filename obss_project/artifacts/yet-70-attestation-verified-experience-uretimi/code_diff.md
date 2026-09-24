# Code Diff — yet-70-attestation-verified-experience-uretimi

## Oluşturulan Dosyalar
- `backend/app/models/attestation.py` — `Attestation` modeli (append-only, `talent_id` denormalize, self-attestation CHECK, `skill_id` nullable)
- `backend/app/models/verified_experience.py` — `VerifiedExperience` modeli (snapshot alanları)
- `backend/app/services/attestation.py` — `create_attestation()`: §3.11 6 kriter kontrolü, tek transaction (Attestation+VerifiedExperience+SkillSignal(koşullu)+AuditEvent+Outbox+Engagement.status→VERIFIED)
- `backend/alembic/versions/f8g9h0i1j2k3_add_attestations_and_verified_experiences.py` — yeni migration (down_revision=ee96f63a4231), **henüz `alembic upgrade head` ile uygulanmadı**

## Değiştirilen Dosyalar
- `backend/app/models/__init__.py` — `Attestation`/`VerifiedExperience` export edildi
- `backend/app/api/engagements.py` — `POST /engagements/{id}/attestations` route'u eklendi (`AttestationCreateRequest`/`AttestationResponse`, `skill_id` opsiyonel alanı dahil)

## AC Karşılanması (özet)
AC-1..AC-9, AC-S1..AC-S5 — servis katmanında sırasıyla: scope kontrolü (`scoped_engagements`), TALENT→403 (S6 istisnası), durum kontrolü (EVALUATED→409), version kontrolü (409), self-attestation (servis + DB CHECK, 409), §3.11 6 kriter → downgrade_reasons, tek transaction commit.

## Review Sürecinde Bulunan ve Düzeltilen Sorun
İlk implementasyon turunda `SkillSignal` oluşturma adımı (AC-1'in Critical bir parçası, STATE_MACHINE.md §5 adım 3'ün zorunlu kıldığı) **yorum satırına alınmış TODO** olarak bırakılmıştı ("hangi skill'e bağlanacağı belirsiz" gerekçesiyle). Bu, orkestratör tarafından `Read` ile tespit edildi (sub-agent'ın kendi özeti bunu "out-of-scope" diye sunmuştu, kabul edilmedi). İkinci bir Haiku dispatch'iyle düzeltildi: `AttestationCreateRequest`'e API.md §2.8'in zaten tanımladığı opsiyonel `skill_id` alanı eklendi, `skill_id` verilip geçerliyse (skills tablosunda var) `SkillSignal` oluşturuluyor, verilmemişse **açık bir koşullu dalda** (yorum satırı değil) atlanıyor.

## Kalan Sınırlamalar
- `skill_id` verilmezse `SkillSignal` oluşturulmuyor — bu, `subject_type=ENGAGEMENT` senaryosunda hangi tek yetkinliğin sinyalleneceğinin istemciden gelmesi gerektiği anlamına geliyor (API.md'nin kendi opsiyonel alan tasarımıyla tutarlı, atdd.md'nin çözülmemiş "Unknowns" maddesiyle uyumlu).
- Revoke ucu, DISPUTED akışı, cooling period — kapsam dışı (atdd.md'de zaten belirtilmiş).
- Migration dosyası oluşturuldu ama **uygulanmadı** — `verify` adımında kullanıcı onayıyla `alembic upgrade head` çalıştırılacak.

## Varsayımlar
- `SkillSignal.strength`: COMPETENCE→STRONG, PARTICIPATION→WEAK (atdd.md'de netleşmemişti, makul eşleme).
- §3.11 kriter 1 (karşılıklı onay) EVALUATED durumuna ulaşmış olmanın implicit kanıtı sayıldı, ayrı kontrol eklenmedi (pratikte tetiklenmeyecek bir downgrade kodu).

## CAVEMAN Self-Review
Yeni dosya sayısı minimum (3 model+servis, 1 migration) — hepsi AC'nin doğrudan gerektirdiği. Ekstra soyutlama/yardımcı fonksiyon yok, mevcut `evaluation.py` deseni birebir takip edildi.
