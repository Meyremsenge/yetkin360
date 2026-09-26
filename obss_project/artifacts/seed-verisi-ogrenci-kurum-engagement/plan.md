# Plan — seed-verisi-ogrenci-kurum-engagement
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, CLI script).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/scripts/seed.py` | Yeni `seed_talents()`, `seed_institutions_and_organizations()`, `seed_engagements()` fonksiyonları eklenecek; mevcut `seed_skills()` ve `if __name__ == "__main__":` bloğu bu yeni fonksiyonları da çağıracak şekilde genişletilecek | medium — mevcut `seed_skills()` davranışı KORUNMALI, sadece genişletilecek |

## New Files
Yok — tek dosyaya (`backend/scripts/seed.py`) eklenecek, yeni bir modül/dosya gerekmiyor (CAVEMAN: script küçük kalacak kadar basit, ayrı dosyalara bölünmesini gerektirecek bir karmaşıklık yok).

## Dependencies

**Kullanılacak (değiştirilmeyecek) servis fonksiyonları ve tam çağrı zinciri** (kod okunarak doğrulandı):

1. `register_user(session, email, password, full_name)` (`app/services/auth.py:130`) — her kullanıcı (20 öğrenci + kurum/organizasyon rolündeki hesaplar) için. **Otomatik olarak boş bir `TalentProfile` da oluşturur** (docstring: "registration never takes a role — role lives on membership, not on User") — kurum/org rolündeki hesaplar da bu yüzden bir `TalentProfile`'a sahip olacak, bu zararsız (kullanılmayacak).
2. `create_institution(name, domain, caller_user_id, session)` (`app/services/institution.py:30`) — 5 kurum, çağıran kullanıcı otomatik ADMIN olur.
3. `invite_member(institution_id, email, role, session)` (`app/services/institution.py:80`) — gerekirse ayrı bir COORDINATOR rolü atamak için (role: "ADMIN" veya "COORDINATOR" — `institutions.py:56-60`'daki şema).
4. `create_organization(...)` (`app/services/organization.py:67`) — organizasyonlar, çağıran otomatik ADMIN olur.
5. `request_institution_link(institution_id, talent_profile_id, session)` (`app/services/institution.py:134`, `Principal.kind == "TALENT"` ile) + `approve_institution_link(request_id, approver_user_id, session)` (`institution.py:184`, COORDINATOR/ADMIN ile) — her öğrenciyi bir kuruma bağlamak için ZORUNLU: `create_engagement`'ın `institution_id` parametresi "talent'ın institution'ıyla eşleşmeli" kontrolü yapıyor (`engagement.py:88`), yani bağlantı önce kurulmalı.
6. `create_engagement(session, principal, talent_id, organization_id, kind, title, institution_id, confidential)` (`app/services/engagement.py:72`) → `DRAFT`. **`DRAFT→PENDING_APPROVAL` geçişinin `institution_id_not_null` ön koşulu var** (`engagement.py:269`) — yani `institution_id` MUTLAKA doldurulmalı, `None` bırakılamaz.
7. `transition_engagement(session, principal, engagement_id, to_status, version, reason)` (`engagement.py:205`) — sırasıyla:
   - `DRAFT→PENDING_APPROVAL`: principal TALENT (kendi engagement'ı) veya ORG_MEMBER/ORG_ADMIN.
   - `PENDING_APPROVAL→ACTIVE`: principal COORDINATOR (kurumun).
   - `ACTIVE→PENDING_EVALUATION`: **`has_deliverable` ön koşulu var** (`engagement.py:297`) — bu adımdan ÖNCE en az bir `create_engagement_task`/`create_deliverable` çağrılmış olmalı; principal ORG_MEMBER/ORG_ADMIN veya COORDINATOR.
8. `create_engagement_task(...)` (`engagement.py:391`) + `create_deliverable(...)` (`engagement.py:516`) — `has_deliverable` ön koşulunu karşılamak için, `PENDING_EVALUATION`'a geçmeden önce.
9. `create_evaluation(session, principal, engagement_id, direction, items, private_note)` (`app/services/evaluation.py:48`) — `direction="ORG_TO_TALENT"` ile (principal ORG_MEMBER/ORG_ADMIN), engagement'ı **otomatik olarak `EVALUATED`'a geçirir** (kod: `AC-2: Triggers engagement.status → EVALUATED transition ONLY for ORG_TO_TALENT`). `items` içindeki `skill_id`'ler `seed_skills()`'in ürettiği gerçek `Skill` kayıtlarına referans vermeli (bu yüzden `seed_skills()` BU fonksiyonlardan ÖNCE çağrılmalı).
10. `create_attestation(session, principal, engagement_id, requested_claim_type, version, skill_id)` (`app/services/attestation.py:150`) — engagement `EVALUATED` olmalı, principal'ın rolü `engagement.institution_id`'nin dolu/boş olmasına göre değişir: **institution_id NOT NULL → sadece COORDINATOR** (`attestation.py:205-210`) attest edebilir (bizim senaryomuzda hepsi institution_id dolu olacağı için hep COORDINATOR). Bu çağrı **tek transaction'da** `Attestation` + `VerifiedExperience` + (varsa) `SkillSignal` + `AuditEvent` + `Outbox` yazar ve engagement'ı `VERIFIED`'a geçirir (AC-3'ün gerektirdiği "gerçek servis fonksiyonu üzerinden" kuralı burada karşılanıyor).

**Principal nesnesi** (`app/services/authorization.py:17`, plain `@dataclass`) — HTTP/cookie login GEREKMİYOR, script doğrudan Python içinde her rol için elle bir `Principal(user_id=..., kind="TALENT"|"ORG_MEMBER"|"ORG_ADMIN"|"COORDINATOR", talent_id=..., org_ids=[...], org_admin_ids=[...], institution_ids=[...], institution_admin_ids=[...], is_platform_admin=False, is_suspended=False)` inşa edip ilgili servis fonksiyonuna geçirebilir.

**Sıra (her engagement için, aynı transaction içinde):**
```
register_user (talent, org_admin, coordinator — daha önce oluşturulmadıysa)
→ create_engagement (DRAFT)
→ transition_engagement (PENDING_APPROVAL, principal=TALENT)
→ transition_engagement (ACTIVE, principal=COORDINATOR)
→ create_engagement_task + create_deliverable (has_deliverable ön koşulu)
→ transition_engagement (PENDING_EVALUATION, principal=ORG_ADMIN)
→ create_evaluation (direction=ORG_TO_TALENT, principal=ORG_ADMIN) → engagement otomatik EVALUATED olur
→ create_attestation (principal=COORDINATOR) → engagement otomatik VERIFIED olur + VerifiedExperience + SkillSignal
```

**Kurum/organizasyon/öğrenci sırası (bir kez, engagement döngüsünden önce):**
```
seed_skills() (mevcut, DEĞİŞMEDEN önce çağrılır — evaluation items skill_id referansı için)
→ 5x register_user (kurum admin/coordinator hesapları) + create_institution
→ Nx register_user (organizasyon admin hesapları) + create_organization (en az 5, 15 engagement'ı dağıtacak kadar)
→ 20x register_user (öğrenci) + request_institution_link + approve_institution_link (her öğrenci 5 kurumdan birine bağlanır)
```

## Migration Required?
**Hayır.** Tüm gerekli tablolar/kolonlar (`users`, `talent_profiles`, `institutions`, `institution_members`, `institution_link_requests`, `organizations`, `organization_members`, `engagements`, `engagement_tasks`, `deliverables`, `evaluations`, `evaluation_items`, `skill_signals`, `attestations`, `verified_experiences`, `audit_events`, `outbox`) zaten migration'larla oluşturulmuş durumda — atdd.md'nin varsayımı doğrulandı.

## Risks
- (atdd.md'den taşındı) ENVIRONMENT koruması: yeni yazılacak fonksiyonlar `if settings.environment == "production": raise` koruması olmadan yazılmamalı (AC-5).
- **Yeni risk (bu adımda bulundu):** Zincir 15 engagement × ~8 servis çağrısı = ~120 çağrı; her biri kendi `session.flush()`/audit_event/outbox yan etkisi üretiyor. Script tek bir dış transaction'a (AC-4) sarılırken, bazı servis fonksiyonları (`create_institution`, `create_engagement` vb.) kendi içlerinde `session.flush()` çağırıyor (commit değil) — bu sorun değil, çünkü nihai `session.commit()`/`rollback()` script'in kendisinde, dış seviyede olacak. Ama servis fonksiyonlarından biri kendi içinde `session.commit()` çağırıyorsa (ör. `register_user`'ın kendi docstring'i "bir transaction içinde" diyor ama gerçek commit noktası `plan` aşamasında `Read` ile TEK TEK doğrulanmalı — code-copilot dispatch prompt'unda bu doğrulama istenmeli, aksi halde kısmi commit'ler idempotency'yi bozabilir.
- Domain/email UNIQUE constraint'leri: 5 kurum için 5 farklı `domain`, kullanıcılar için farklı `email` gerekiyor — idempotency kontrolü (AC-2) email/domain üzerinden yapılmalı (mevcut `seed_skills()`'in slug kontrolü kalıbıyla tutarlı).

## Open Questions
Yok (ilk yazımda) — ama test-copilot adımında GERÇEK bir çelişki bulundu, burada çözülüyor:

## Kararlar (test-copilot sonrası eklendi)
**"20 öğrenci" sayımı nasıl yapılacak?** `register_user()` her kullanıcı için otomatik bir `TalentProfile` oluşturuyor (docstring: "role lives on membership, not on User") — yani kurum admin/coordinator ve organizasyon admin hesapları da birer `TalentProfile` alacak. `TalentProfile` tablosunun TAMAMINI saymak "tam 20" testini bozar (toplam öğrenci+kurum admin+org admin sayısı 20'den fazla olur).

**Karar: e-posta önek konvansiyonu ile ayrım.**
- Öğrenci hesapları: `ogrenci{1..20}@seed.local`
- Kurum admin/coordinator hesapları: `kurum{1..5}-admin@seed.local`
- Organizasyon admin hesapları: `org{1..N}-admin@seed.local`

`test_seed.py`'nin "20 TalentProfile" sayımı `User.email LIKE 'ogrenci%@seed.local'` filtresiyle YAPILMALI (ham `TalentProfile` tablosu sayımı değil). `code-copilot` bu e-posta önek konvansiyonuna BİREBİR uymalı — aksi halde test hem doğru bir implementasyonda hem yanlış bir implementasyonda aynı şekilde kırılabilir.
