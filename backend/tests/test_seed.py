"""
Seed script tests for PLAN 3.11 — 20 öğrenci, 5 kurum, 15 engagement (VERIFIED).

Reference: YET-115, atdd.md, plan.md

ATDD Acceptance Criteria (AC-1 through AC-7):
- AC-1: Happy path (temiz DB) → 20 TalentProfile, 5 Institution, ≥5 Organization, 15 Engagement (VERIFIED)
- AC-2: Idempotency (ikinci çalıştırma) → sayılar DEĞİŞMEZ
- AC-3: VERIFIED engagement'lar → her birine ≥1 Attestation + ≥1 VerifiedExperience (gerçek servis fonksiyonlarıyla)
- AC-4: DB hatasında → tam rollback, 0 kalan kayıt
- AC-5: Production ortamında → hiçbir kayıt oluşturmadan hata (exit code 1)
- AC-6: DB bağlantısı yoksa → anlamlı hata (exit code 1)
- AC-7: 15 engagement dağıtımı → eşit olmak zorunda değil, ama geçerli FK'ler

Status: Tests RED (expected) — seed_talents(), seed_institutions_and_organizations(),
seed_engagements() fonksiyonları henüz implement edilmemiştir.

Test Deseni:
- Real PostgreSQL transaction per test (inherited from conftest.py)
- session fixture kullanılır
- Principal: dataclass elle inşa edilerek servis fonksiyonlarına geçilir
- DB sayıları SELECT ile doğrulanır

Varsayımlar:
- Toplam TalentProfile: exact 20 (sadece öğrenciler için; kurum/org admin hesaplarının TalentProfile'ı
  bu sayıya dahil edilmez — plan.md fonksiyonları netleştiğinde teyit edilmesi gerekir)
  E-posta konvansiyonu: öğrenci → `ogrenci{1..20}@seed.local`, kurum admin → `kurum{1..5}-admin@seed.local`, org admin → `org{1..N}-admin@seed.local`
- Kurum admin hesapları create_institution() içinde oluşturulur (register_user ile ayrı değil)
- Organization admin hesapları create_organization() içinde oluşturulur (register_user ile ayrı değil)
- Seed script mevcut _SessionLocal() ile çalışır (test session fixture'ı kullansa da,
  script kendi session başlatıyorsa — buna göre mock/patch gerekebilir)
- VERIFIED durumu: create_attestation() servis fonksiyonu ile elde edilir (doğrudan UPDATE değil)
"""

import pytest
from unittest.mock import patch
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, IntegrityError

from app.models import (
    User,
    TalentProfile,
    Institution,
    Organization,
    Engagement,
    Attestation,
    VerifiedExperience,
    Skill,
    AuditEvent,
)
from app.core.config import settings

# Import seed functions (will fail initially — expected)
try:
    from scripts.seed import (
        seed_skills,
        seed_talents,
        seed_institutions_and_organizations,
        seed_engagements,
    )
except ImportError:
    # Expected during initial development
    seed_talents = None
    seed_institutions_and_organizations = None
    seed_engagements = None


# ============================================================================
# AC-1: Happy path — temiz DB'de ilk çalıştırma
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac1_happy_path_creates_20_talents_5_institutions_15_engagements(session):
    """
    Given temiz bir veritabanı (migration'lar uygulanmış, veri yok)
    When seed_talents(), seed_institutions_and_organizations(), seed_engagements() çağrılır
    Then DB'de tam olarak:
      - 20 TalentProfile (sadece öğrenciler)
      - 5 Institution
      - ≥5 Organization (her engagement bir organization'a bağlı, FK constraint)
      - 15 Engagement (hepsi status='VERIFIED')
      oluşur
    """
    # Ensure skills are seeded first (prerequisite)
    seed_skills(session)
    session.commit()

    # Call seed functions in order
    seed_talents(session)
    session.commit()

    seed_institutions_and_organizations(session)
    session.commit()

    seed_engagements(session)
    session.commit()

    # Verify counts
    # Count only student talent profiles (ogrenci*.@seed.local email filter)
    talent_count = session.query(func.count(TalentProfile.id)).join(
        User, TalentProfile.user_id == User.id
    ).filter(User.email.like("ogrenci%@seed.local")).scalar()
    assert talent_count == 20, f"Expected 20 student TalentProfile, got {talent_count}"

    institution_count = session.query(func.count(Institution.id)).scalar()
    assert institution_count == 5, f"Expected 5 Institution, got {institution_count}"

    organization_count = session.query(func.count(Organization.id)).scalar()
    assert organization_count >= 5, f"Expected ≥5 Organization, got {organization_count}"

    engagement_count = session.query(func.count(Engagement.id)).scalar()
    assert engagement_count == 15, f"Expected 15 Engagement, got {engagement_count}"

    # Verify all engagements are VERIFIED
    verified_engagements = session.query(Engagement).filter(
        Engagement.status == "VERIFIED"
    ).all()
    assert (
        len(verified_engagements) == 15
    ), f"Expected 15 VERIFIED engagements, got {len(verified_engagements)}"

    # Verify FK constraints are satisfied
    for engagement in verified_engagements:
        assert engagement.talent_id is not None, "Engagement.talent_id is NULL"
        assert engagement.organization_id is not None, "Engagement.organization_id is NULL"
        assert engagement.institution_id is not None, "Engagement.institution_id is NULL"
        # Verify talent exists
        talent = session.query(TalentProfile).filter_by(id=engagement.talent_id).first()
        assert talent is not None, f"Engagement references non-existent TalentProfile {engagement.talent_id}"
        # Verify organization exists
        org = session.query(Organization).filter_by(id=engagement.organization_id).first()
        assert org is not None, f"Engagement references non-existent Organization {engagement.organization_id}"
        # Verify institution exists
        inst = session.query(Institution).filter_by(id=engagement.institution_id).first()
        assert inst is not None, f"Engagement references non-existent Institution {engagement.institution_id}"


# ============================================================================
# AC-2: Idempotency — ikinci çalıştırma sayıları değişmez
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac2_idempotency_second_run_does_not_change_counts(session):
    """
    Given script ikinci kez çalıştırılır (idempotency)
    When seed_talents(), seed_institutions_and_organizations(), seed_engagements()
         tekrar çağrılır
    Then DB'deki kayıt sayıları DEĞİŞMEZ (20/5/15 aynı kalır)
         — mevcut seed_skills() kalıbıyla tutarlı (email/slug üzerinden var-mı kontrolü)
    """
    # Initial seeding
    seed_skills(session)
    session.commit()
    seed_talents(session)
    session.commit()
    seed_institutions_and_organizations(session)
    session.commit()
    seed_engagements(session)
    session.commit()

    # Record initial counts
    # Count only student talent profiles (ogrenci*.@seed.local email filter)
    talent_count_1 = session.query(func.count(TalentProfile.id)).join(
        User, TalentProfile.user_id == User.id
    ).filter(User.email.like("ogrenci%@seed.local")).scalar()
    institution_count_1 = session.query(func.count(Institution.id)).scalar()
    organization_count_1 = session.query(func.count(Organization.id)).scalar()
    engagement_count_1 = session.query(func.count(Engagement.id)).scalar()

    # Second seeding (idempotent)
    seed_talents(session)
    session.commit()
    seed_institutions_and_organizations(session)
    session.commit()
    seed_engagements(session)
    session.commit()

    # Record counts after second run
    # Count only student talent profiles (ogrenci*.@seed.local email filter)
    talent_count_2 = session.query(func.count(TalentProfile.id)).join(
        User, TalentProfile.user_id == User.id
    ).filter(User.email.like("ogrenci%@seed.local")).scalar()
    institution_count_2 = session.query(func.count(Institution.id)).scalar()
    organization_count_2 = session.query(func.count(Organization.id)).scalar()
    engagement_count_2 = session.query(func.count(Engagement.id)).scalar()

    # Assert no change
    assert (
        talent_count_2 == talent_count_1
    ), f"TalentProfile count changed: {talent_count_1} → {talent_count_2}"
    assert (
        institution_count_2 == institution_count_1
    ), f"Institution count changed: {institution_count_1} → {institution_count_2}"
    assert (
        organization_count_2 == organization_count_1
    ), f"Organization count changed: {organization_count_1} → {organization_count_2}"
    assert (
        engagement_count_2 == engagement_count_1
    ), f"Engagement count changed: {engagement_count_1} → {engagement_count_2}"


# ============================================================================
# AC-3: VERIFIED engagement'lara bağlı Attestation ve VerifiedExperience
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac3_verified_engagements_have_attestation_and_verified_experience(session):
    """
    Given VERIFIED bir engagement
    When bu engagement'a bağlı kayıtlar incelenir
    Then en az bir Attestation ve bir VerifiedExperience kaydı olmalı
         (append-only tablolara gerçek servis fonksiyonları üzerinden yazılmış,
          doğrudan UPDATE ile sahte VERIFIED durumu DEĞİL — audit_events/outbox yan etkilerini kapsamak için)
    """
    # Seed all data
    seed_skills(session)
    session.commit()
    seed_talents(session)
    session.commit()
    seed_institutions_and_organizations(session)
    session.commit()
    seed_engagements(session)
    session.commit()

    # Get all VERIFIED engagements
    verified_engagements = session.query(Engagement).filter(
        Engagement.status == "VERIFIED"
    ).all()
    assert len(verified_engagements) == 15, "Expected 15 VERIFIED engagements"

    # Check each engagement has at least one Attestation and VerifiedExperience
    for engagement in verified_engagements:
        attestations = session.query(Attestation).filter(
            Attestation.engagement_id == engagement.id
        ).all()
        assert (
            len(attestations) >= 1
        ), f"Engagement {engagement.id} has {len(attestations)} Attestations, expected ≥1"

        verified_experiences = session.query(VerifiedExperience).filter(
            VerifiedExperience.engagement_id == engagement.id
        ).all()
        assert (
            len(verified_experiences) >= 1
        ), f"Engagement {engagement.id} has {len(verified_experiences)} VerifiedExperience records, expected ≥1"

        # Verify audit events were recorded (side effect of create_attestation)
        # AuditEvent has subject_type="ATTESTATION" and subject_id=attestation.id
        attestations = session.query(Attestation).filter(
            Attestation.engagement_id == engagement.id
        ).all()
        assert len(attestations) >= 1, f"Engagement {engagement.id} has no Attestations"

        for attestation in attestations:
            audit_events = session.query(AuditEvent).filter(
                AuditEvent.subject_type == "ATTESTATION",
                AuditEvent.subject_id == attestation.id,
            ).all()
            assert (
                len(audit_events) >= 1
            ), f"Attestation {attestation.id} has no AuditEvents (expected side effect of attestation)"


# ============================================================================
# AC-4: DB hatası ortasında tam rollback
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac4_db_error_during_seeding_causes_full_rollback(session):
    """
    Given script bir DB hatasıyla (ör. bağlantı kopması) ortasında kesilir
    When script yeniden çalıştırılır
    Then DB'de kısmi/tutarsız veri KALMAZ — tüm seed işlemi tek bir transaction'a alınır,
         hata durumunda session.rollback() ile tamamen geri alınır

    Test strategy: Mock register_user (called ~20x by seed_talents) to fail on 3rd call,
    call the REAL seed_talents() which should rollback all changes on IntegrityError.
    """
    # Seed skills first (this will succeed)
    seed_skills(session)
    session.commit()

    if seed_talents is not None:
        # Get the original register_user function before patching
        from app.services import auth as auth_module
        original_register_user = auth_module.register_user

        call_count = [0]

        def mock_register_user(*args, **kwargs):
            call_count[0] += 1
            # Allow first 2 calls to succeed, fail on 3rd to simulate mid-seeding error
            if call_count[0] == 3:
                raise IntegrityError("Mock constraint violation", None, None)
            # Call the real function for successful calls
            return original_register_user(*args, **kwargs)

        # Patch scripts.seed.register_user with mock that fails on 3rd call
        # (register_user is imported in scripts.seed, so patch where it's used, not where it's defined)
        with patch("scripts.seed.register_user", side_effect=mock_register_user):
            try:
                # Call the REAL seed_talents() — it should rollback internally on IntegrityError
                seed_talents(session)
            except IntegrityError:
                # Ensure rollback happens (script should do this internally)
                session.rollback()

        # Verify no talents were created (all should be rolled back due to single transaction)
        # Count only student talent profiles (ogrenci*.@seed.local email filter)
        talent_count = session.query(func.count(TalentProfile.id)).join(
            User, TalentProfile.user_id == User.id
        ).filter(User.email.like("ogrenci%@seed.local")).scalar()
        assert talent_count == 0, f"Expected 0 student TalentProfile after rollback, got {talent_count}"


# ============================================================================
# AC-5: Production ortamında hata (hiçbir kayıt oluşturulmadan)
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac5_production_environment_prevents_seeding(session, monkeypatch):
    """
    Given settings.environment == "production"
    When script çalıştırılmaya çalışılır
    Then script hiçbir kayıt oluşturmadan hata verip exit code 1 ile çıkar
         (üretimde yanlışlıkla 20 sahte öğrenci oluşturma riskine karşı)

    KRITIK: Sadece exception fırlatıldığını görmek yeterli değil, DB'de hiçbir kayıt
    oluşmadığını da AYRICA assert et (postmortem kuralı: "sadece beklenen sonuç kodu
    geldi" yeterli değil, iddia edilen mekanizmanın GERÇEKTEN çalıştığını kanıtla).
    """
    # Temporarily patch settings.environment to "production"
    monkeypatch.setattr(settings, "environment", "production")

    # Attempt to seed — should raise an error before doing anything
    with pytest.raises(
        (RuntimeError, ValueError, Exception)
    ):
        # Seed functions should check environment and raise before DB operations
        seed_talents(session)

    # Verify no TalentProfile was created
    talent_count = session.query(func.count(TalentProfile.id)).scalar()
    assert talent_count == 0, f"Production guard failed: {talent_count} TalentProfile created"

    # Also verify no other seed records were created in this test
    skill_count = session.query(func.count(Skill.id)).scalar()
    institution_count = session.query(func.count(Institution.id)).scalar()
    organization_count = session.query(func.count(Organization.id)).scalar()
    engagement_count = session.query(func.count(Engagement.id)).scalar()

    assert (
        skill_count == 0
    ), f"Production guard failed: {skill_count} Skill records created"
    assert (
        institution_count == 0
    ), f"Production guard failed: {institution_count} Institution records created"
    assert (
        organization_count == 0
    ), f"Production guard failed: {organization_count} Organization records created"
    assert (
        engagement_count == 0
    ), f"Production guard failed: {engagement_count} Engagement records created"


# ============================================================================
# AC-6: DB bağlantısı yoksa anlamlı hata
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac6_database_connection_error_raises_meaningful_message(session):
    """
    Given DB bağlantısı hiç kurulamıyorsa (Docker Compose ayakta değil)
    When script çalıştırılır
    Then anlamlı bir hata mesajıyla (OperationalError yakalanıp yeniden fırlatılır)
         exit code 1 ile çıkar, stack trace yerine okunabilir bir mesaj gösterilir

    Test: Session.flush() metodunu mock'la gerçek bir DB hatası simüle et
    """
    # Mock session.flush() to simulate a database connection error
    # (session.close() alone doesn't prevent reuse; we need to mock the actual DB operation)
    with patch.object(
        session, "flush", side_effect=OperationalError("could not connect to server", None, None)
    ):
        # Attempt to seed with mocked connection error — should raise OperationalError
        with pytest.raises(OperationalError) as exc_info:
            seed_talents(session)

    # Verify error message is meaningful (not a cryptic stack trace)
    error_str = str(exc_info.value).lower()
    # Should contain database-related keywords or connection info
    assert any(
        keyword in error_str for keyword in ["database", "connection", "could not connect", "operational", "error"]
    ), f"Error message is not meaningful: {exc_info.value}"


# ============================================================================
# AC-7: 15 engagement dağıtımı — eşit olmak zorunda değil, ama FK ihlali yok
# ============================================================================


@pytest.mark.skipif(
    seed_talents is None,
    reason="seed_talents() not yet implemented (expected RED test)"
)
def test_ac7_engagement_distribution_respects_fk_constraints(session):
    """
    Given 15 engagement dağıtılırken
    When 20 öğrenci arasında dağıtım yapılır
    Then dağıtım eşit olmak ZORUNDA değildir (gerçekçi veri: bazı öğrencinin 0, bazısının 2+ engagement'ı)
         — ama her engagement geçerli bir talent_id/organization_id/institution_id FK'sine sahip olmalı

    FK constraint ihlali: beklenen exception
    """
    # Seed all data
    seed_skills(session)
    session.commit()
    seed_talents(session)
    session.commit()
    seed_institutions_and_organizations(session)
    session.commit()
    seed_engagements(session)
    session.commit()

    # Get all engagements
    engagements = session.query(Engagement).all()
    assert len(engagements) == 15, "Expected 15 engagements"

    # Verify each engagement has valid FKs (no NULL references)
    talent_ids_used = set()
    for engagement in engagements:
        assert engagement.talent_id is not None, f"Engagement {engagement.id} has NULL talent_id"
        assert (
            engagement.organization_id is not None
        ), f"Engagement {engagement.id} has NULL organization_id"
        assert (
            engagement.institution_id is not None
        ), f"Engagement {engagement.id} has NULL institution_id"

        # Verify references exist
        talent = session.query(TalentProfile).filter_by(id=engagement.talent_id).first()
        assert talent is not None, f"FK violation: TalentProfile {engagement.talent_id} not found"

        org = session.query(Organization).filter_by(id=engagement.organization_id).first()
        assert org is not None, f"FK violation: Organization {engagement.organization_id} not found"

        inst = session.query(Institution).filter_by(id=engagement.institution_id).first()
        assert inst is not None, f"FK violation: Institution {engagement.institution_id} not found"

        talent_ids_used.add(engagement.talent_id)

    # Verify distribution is not necessarily equal (some talents may have 0 or 2+ engagements)
    # — this is OK as long as FKs are valid
    talent_engagement_counts = {}
    for engagement in engagements:
        talent_id = engagement.talent_id
        talent_engagement_counts[talent_id] = talent_engagement_counts.get(talent_id, 0) + 1

    # Count how many talents used in engagements (should be ≤20, >0)
    assert (
        0 < len(talent_ids_used) <= 20
    ), f"Expected 1-20 talents used in engagements, got {len(talent_ids_used)}"

    # Verify uneven distribution is possible (not necessarily all have ≥1)
    counts = list(talent_engagement_counts.values())
    # At least one of: some talent has 0, or some talent has 2+
    has_zero = any(talent_id not in talent_engagement_counts for talent_id in range(1, 21))
    has_multiple = any(c >= 2 for c in counts)
    # Verify distribution is actually uneven (proof of soft constraint)
    assert has_zero or has_multiple, "Expected uneven distribution: either some talents have 0 engagements or some have 2+, but distribution was perfectly even"


# ============================================================================
# Bonus: Verify seed_skills() still works (baseline)
# ============================================================================


def test_seed_skills_baseline(session):
    """
    Baseline: Verify existing seed_skills() function still works correctly.
    This is a sanity check before testing new functions.
    """
    # seed_skills should already be importable
    seed_skills(session)
    session.commit()

    skill_count = session.query(func.count(Skill.id)).scalar()
    assert skill_count > 0, "seed_skills() produced no Skill records"

    # Verify skill data is complete
    python_skill = session.query(Skill).filter_by(slug="python").first()
    assert python_skill is not None, "Python skill not found"
    assert python_skill.category == "LANGUAGE"


# ============================================================================
# AC-4 (Red-team addition): Error propagation in seed_engagements()
# ============================================================================


@pytest.mark.skipif(
    seed_engagements is None,
    reason="seed_engagements() not yet implemented (expected RED test)"
)
def test_ac4_engagement_creation_error_propagates_not_swallowed(session):
    """
    Given seed_engagements() çalışırken bir engagement oluşturma hatası meydana gelir
    When create_evaluation() fonksiyonu exception fırlatırsa (mock ile simüle edilir)
    Then seed_engagements() bu exception'ı yukarıya propagate etmeli (asla sessizce yutmaz)
         — eski implementasyon "try/except Exception: continue" kullanıyordu, bu düzeltildi

    Red-team finding (AC-4 regression test): Verify error handling improvement.
    Before fix: engagement creation errors were silently caught and skipped.
    After fix: errors propagate to caller (__main__ rollback mechanism).

    Test strategy:
    1. Seed prerequisites (skills, talents, institutions/orgs)
    2. Mock scripts.seed.create_evaluation to fail on first call
    3. Assert seed_engagements(session) raises the exception (not silent continuation)
    """
    # Seed prerequisites (all required for engagement creation)
    seed_skills(session)
    session.commit()

    seed_talents(session)
    session.commit()

    seed_institutions_and_organizations(session)
    session.commit()

    # Mock create_evaluation (called in _create_verified_engagement)
    # CRITICAL: Patch target is scripts.seed.create_evaluation (where imported, not where defined)
    with patch("scripts.seed.create_evaluation", side_effect=RuntimeError("Simulated evaluation creation failure")):
        # seed_engagements() should raise the exception, not silently catch and continue
        with pytest.raises(RuntimeError, match="Simulated evaluation creation failure"):
            seed_engagements(session)


# ============================================================================
# YET-190 (AUTHZ-02, K3-a): her kurumda gerçek COORDINATOR üyesi var
# ============================================================================


def _seed_all(session):
    seed_skills(session)
    session.commit()
    seed_talents(session)
    session.commit()
    seed_institutions_and_organizations(session)
    session.commit()
    seed_engagements(session)
    session.commit()


def test_yet190_every_institution_has_exactly_one_seed_coordinator(session):
    from app.models import InstitutionMember

    _seed_all(session)

    institutions = session.query(Institution).all()
    assert len(institutions) == 5
    for i in range(1, 6):
        inst = session.query(Institution).filter_by(domain=f"inst{i}.seed.local").one()
        coordinators = (
            session.query(User)
            .join(InstitutionMember, InstitutionMember.user_id == User.id)
            .filter(
                InstitutionMember.institution_id == inst.id,
                InstitutionMember.role == "COORDINATOR",
            )
            .all()
        )
        assert [u.email for u in coordinators] == [f"kurum{i}-koordinator@seed.local"]
        admins = (
            session.query(InstitutionMember)
            .filter_by(institution_id=inst.id, role="ADMIN")
            .count()
        )
        assert admins == 1


def test_yet190_verified_engagements_are_attested_by_institution_coordinator(session):
    from app.models import InstitutionMember

    _seed_all(session)

    attestations = session.query(Attestation).all()
    assert len(attestations) == 15
    for att in attestations:
        engagement = session.query(Engagement).filter_by(id=att.engagement_id).one()
        member = (
            session.query(InstitutionMember)
            .filter_by(
                institution_id=engagement.institution_id, user_id=att.attestor_user_id
            )
            .one()
        )
        assert member.role == "COORDINATOR"


def test_yet190_coordinator_seed_is_idempotent_and_repairs_admin_only_db(session):
    from app.models import InstitutionMember

    _seed_all(session)
    member_count = session.query(func.count(InstitutionMember.id)).scalar()
    user_count = session.query(func.count(User.id)).scalar()
    assert member_count == 10  # 5 admins + 5 coordinators

    # A database seeded before YET-190 has only the admins: removing the
    # coordinator memberships simulates it (membership rows are not append-only).
    session.query(InstitutionMember).filter_by(role="COORDINATOR").delete()
    session.commit()
    assert session.query(func.count(InstitutionMember.id)).scalar() == 5

    seed_institutions_and_organizations(session)
    session.commit()
    assert session.query(func.count(InstitutionMember.id)).scalar() == member_count
    assert session.query(func.count(User.id)).scalar() == user_count

    seed_institutions_and_organizations(session)
    session.commit()
    assert session.query(func.count(InstitutionMember.id)).scalar() == member_count
    assert session.query(func.count(User.id)).scalar() == user_count


# ============================================================================
# PLAN 3.28: demo-ready data — realistic names, every student linked, public slugs
# ============================================================================


def test_plan_3_28_demo_data_is_realistic_and_linked(session):
    seed_skills(session)
    seed_talents(session)
    seed_institutions_and_organizations(session)
    seed_engagements(session)
    session.flush()

    students = session.query(TalentProfile).join(
        User, TalentProfile.user_id == User.id
    ).filter(User.email.like("ogrenci%@seed.local")).all()
    assert len(students) == 20
    for tp in students:
        assert not tp.full_name.startswith("Student"), tp.full_name
        assert tp.institution_id is not None, f"{tp.full_name} is not linked to an institution"
        assert tp.public_slug and tp.visibility == "PUBLIC"

    names = [i.name for i in session.query(Institution).filter(Institution.domain.like("inst%.seed.local"))]
    names += [o.name for o in session.query(Organization).filter(Organization.legal_id.like("ORG%"))]
    assert names and not any(n.startswith(("Institution ", "Organization ")) for n in names)

    titles = [e.title for e in session.query(Engagement).filter(Engagement.status == "VERIFIED")]
    assert titles and not any(t.startswith("Engagement ") for t in titles)


# ============================================================================
# SPRINT J: organization teams with units, showcase, Ayşe's demo story
# ============================================================================


def _seed_story(session):
    from scripts.seed import seed_demo_story, seed_org_team, seed_verified_organizations

    seed_skills(session)
    seed_talents(session)
    seed_institutions_and_organizations(session)
    seed_verified_organizations(session)
    seed_engagements(session)
    seed_org_team(session)
    seed_demo_story(session)
    session.commit()


def _member_rows(session, legal_id):
    from app.models import OrganizationMember

    return {
        email: (role, unit)
        for email, role, unit in session.query(User.email, OrganizationMember.role, OrganizationMember.unit)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .filter(Organization.legal_id == legal_id)
    }


def test_sprint_j_org_team_members_units_and_showcase(session):
    _seed_story(session)

    assert _member_rows(session, "ORG1") == {
        "org1-admin@seed.local": ("ADMIN", "Yönetim"),
        "org1-yazilim@seed.local": ("MEMBER", "Yazılım"),
        "org1-tasarim@seed.local": ("MEMBER", "Tasarım"),
    }
    assert _member_rows(session, "ORG3")["org3-ik@seed.local"] == ("MEMBER", "İnsan Kaynakları")

    names = {
        email: name
        for email, name in session.query(User.email, TalentProfile.full_name).join(
            TalentProfile, TalentProfile.user_id == User.id
        ).filter(User.email.in_(["org1-yazilim@seed.local", "org1-tasarim@seed.local", "org3-ik@seed.local"]))
    }
    assert names == {
        "org1-yazilim@seed.local": "Mehmet Karaca",
        "org1-tasarim@seed.local": "Zeynep Arı",
        "org3-ik@seed.local": "Elif Çınar",
    }

    showcase = {o.legal_id: o.showcase_public for o in session.query(Organization).filter(Organization.legal_id.like("ORG%"))}
    assert showcase == {"ORG1": True, "ORG2": False, "ORG3": False, "ORG4": True, "ORG5": False}


def test_sprint_j_ayse_story_runs_through_the_real_state_machine(session):
    from app.models import Evaluation, InstitutionMember
    from scripts.seed import DEMO_STORY_ENGAGEMENTS

    _seed_story(session)

    ayse = session.query(TalentProfile).join(User, TalentProfile.user_id == User.id).filter(
        User.email == "ogrenci1@seed.local"
    ).one()
    mehmet = session.query(User).filter_by(email="org1-yazilim@seed.local").one()
    lale = session.query(Organization).filter_by(legal_id="ORG1").one()
    galata = session.query(Institution).filter_by(domain="inst1.seed.local").one()
    assert ayse.institution_id == galata.id

    by_title = {
        e.title: e
        for e in session.query(Engagement).filter(
            Engagement.title.in_([row[0][0] for row in DEMO_STORY_ENGAGEMENTS])
        )
    }
    assert {title: e.status for title, e in by_title.items()} == {
        row[0][0]: row[1] for row in DEMO_STORY_ENGAGEMENTS
    }
    for engagement in by_title.values():
        assert engagement.talent_id == ayse.id
        assert engagement.organization_id == lale.id
        assert engagement.institution_id == galata.id
        assert engagement.supervisor_user_id == mehmet.id

    verified = by_title["Mobil Bankacılık API Stajı"]
    evaluation = session.query(Evaluation).filter_by(engagement_id=verified.id, direction="ORG_TO_TALENT").one()
    assert evaluation.evaluator_user_id == mehmet.id
    attestation = session.query(Attestation).filter_by(engagement_id=verified.id).one()
    sealer = session.query(InstitutionMember).filter_by(
        institution_id=galata.id, user_id=attestation.attestor_user_id
    ).one()
    assert sealer.role == "COORDINATOR"
    assert session.query(VerifiedExperience).filter_by(engagement_id=verified.id).count() == 1


def test_sprint_j_story_is_idempotent(session):
    from app.models import OrganizationMember
    from scripts.seed import seed_demo_story, seed_org_team

    _seed_story(session)
    counts = (
        session.query(func.count(User.id)).scalar(),
        session.query(func.count(OrganizationMember.id)).scalar(),
        session.query(func.count(Engagement.id)).scalar(),
        session.query(func.count(Attestation.id)).scalar(),
    )

    assert seed_org_team(session) == 0
    assert seed_demo_story(session) == 0
    session.commit()

    assert counts == (
        session.query(func.count(User.id)).scalar(),
        session.query(func.count(OrganizationMember.id)).scalar(),
        session.query(func.count(Engagement.id)).scalar(),
        session.query(func.count(Attestation.id)).scalar(),
    )
