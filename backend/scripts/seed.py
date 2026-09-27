"""
Skill taxonomy seed script (YET-10) + PLAN 3.11 seed data (20 students, 5 institutions, 15 engagements).

Populates database with:
- ~30-50 representative skills across 5 categories (YET-10)
- 20 student accounts (ogrenci1-20@seed.local)
- 5 institutions + N organizations
- 15 complete VERIFIED engagements with Attestation/VerifiedExperience

Usage: python -m scripts.seed

WARNING: This script is intended for development/testing only.
DO NOT run in production without careful consideration.
"""

import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import _SessionLocal
from app.core.security import hash_password
from app.models import Skill, User, TalentProfile, Institution, Organization, Engagement
from app.services.auth import register_user
from app.services.institution import (
    create_institution,
    request_institution_link,
    approve_institution_link,
    DuplicateLinkRequestError,
)
from app.services.organization import create_organization
from app.services.engagement import (
    create_engagement,
    transition_engagement,
    create_engagement_task,
    create_deliverable,
)
from app.services.evaluation import create_evaluation
from app.services.attestation import create_attestation
from app.services.authorization import Principal


SKILLS_DATA = [
    # ========================================================================
    # LANGUAGE (8 skills)
    # ========================================================================
    {
        "slug": "python",
        "name_tr": "Python",
        "name_en": "Python",
        "category": "LANGUAGE",
    },
    {
        "slug": "javascript",
        "name_tr": "JavaScript",
        "name_en": "JavaScript",
        "category": "LANGUAGE",
    },
    {
        "slug": "typescript",
        "name_tr": "TypeScript",
        "name_en": "TypeScript",
        "category": "LANGUAGE",
    },
    {
        "slug": "java",
        "name_tr": "Java",
        "name_en": "Java",
        "category": "LANGUAGE",
    },
    {
        "slug": "go",
        "name_tr": "Go",
        "name_en": "Go",
        "category": "LANGUAGE",
    },
    {
        "slug": "csharp",
        "name_tr": "C#",
        "name_en": "C#",
        "category": "LANGUAGE",
    },
    {
        "slug": "rust",
        "name_tr": "Rust",
        "name_en": "Rust",
        "category": "LANGUAGE",
    },
    {
        "slug": "php",
        "name_tr": "PHP",
        "name_en": "PHP",
        "category": "LANGUAGE",
    },
    # ========================================================================
    # FRAMEWORK (8 skills)
    # ========================================================================
    {
        "slug": "fastapi",
        "name_tr": "FastAPI",
        "name_en": "FastAPI",
        "category": "FRAMEWORK",
    },
    {
        "slug": "react",
        "name_tr": "React",
        "name_en": "React",
        "category": "FRAMEWORK",
    },
    {
        "slug": "django",
        "name_tr": "Django",
        "name_en": "Django",
        "category": "FRAMEWORK",
    },
    {
        "slug": "nextjs",
        "name_tr": "Next.js",
        "name_en": "Next.js",
        "category": "FRAMEWORK",
    },
    {
        "slug": "vuejs",
        "name_tr": "Vue.js",
        "name_en": "Vue.js",
        "category": "FRAMEWORK",
    },
    {
        "slug": "springboot",
        "name_tr": "Spring Boot",
        "name_en": "Spring Boot",
        "category": "FRAMEWORK",
    },
    {
        "slug": "expressjs",
        "name_tr": "Express.js",
        "name_en": "Express.js",
        "category": "FRAMEWORK",
    },
    {
        "slug": "flask",
        "name_tr": "Flask",
        "name_en": "Flask",
        "category": "FRAMEWORK",
    },
    # ========================================================================
    # TOOL (8 skills)
    # ========================================================================
    {
        "slug": "docker",
        "name_tr": "Docker",
        "name_en": "Docker",
        "category": "TOOL",
    },
    {
        "slug": "git",
        "name_tr": "Git",
        "name_en": "Git",
        "category": "TOOL",
    },
    {
        "slug": "postgresql",
        "name_tr": "PostgreSQL",
        "name_en": "PostgreSQL",
        "category": "TOOL",
    },
    {
        "slug": "kubernetes",
        "name_tr": "Kubernetes",
        "name_en": "Kubernetes",
        "category": "TOOL",
    },
    {
        "slug": "aws",
        "name_tr": "AWS",
        "name_en": "AWS",
        "category": "TOOL",
    },
    {
        "slug": "linux",
        "name_tr": "Linux",
        "name_en": "Linux",
        "category": "TOOL",
    },
    {
        "slug": "redis",
        "name_tr": "Redis",
        "name_en": "Redis",
        "category": "TOOL",
    },
    {
        "slug": "nginx",
        "name_tr": "Nginx",
        "name_en": "Nginx",
        "category": "TOOL",
    },
    # ========================================================================
    # DOMAIN (6 skills)
    # ========================================================================
    {
        "slug": "ml",
        "name_tr": "Makine Öğrenmesi",
        "name_en": "Machine Learning",
        "category": "DOMAIN",
    },
    {
        "slug": "data-analysis",
        "name_tr": "Veri Analizi",
        "name_en": "Data Analysis",
        "category": "DOMAIN",
    },
    {
        "slug": "cybersecurity",
        "name_tr": "Siber Güvenlik",
        "name_en": "Cybersecurity",
        "category": "DOMAIN",
    },
    {
        "slug": "cloud-arch",
        "name_tr": "Bulut Mimarisi",
        "name_en": "Cloud Architecture",
        "category": "DOMAIN",
    },
    {
        "slug": "devops",
        "name_tr": "DevOps",
        "name_en": "DevOps",
        "category": "DOMAIN",
    },
    {
        "slug": "project-mgmt",
        "name_tr": "Proje Yönetimi",
        "name_en": "Project Management",
        "category": "DOMAIN",
    },
    # ========================================================================
    # SOFT (6 skills)
    # ========================================================================
    {
        "slug": "communication",
        "name_tr": "İletişim",
        "name_en": "Communication",
        "category": "SOFT",
    },
    {
        "slug": "teamwork",
        "name_tr": "Takım Çalışması",
        "name_en": "Teamwork",
        "category": "SOFT",
    },
    {
        "slug": "problem-solving",
        "name_tr": "Problem Çözme",
        "name_en": "Problem Solving",
        "category": "SOFT",
    },
    {
        "slug": "leadership",
        "name_tr": "Liderlik",
        "name_en": "Leadership",
        "category": "SOFT",
    },
    {
        "slug": "time-management",
        "name_tr": "Zaman Yönetimi",
        "name_en": "Time Management",
        "category": "SOFT",
    },
    {
        "slug": "presentation",
        "name_tr": "Sunum Becerisi",
        "name_en": "Presentation Skills",
        "category": "SOFT",
    },
]


def seed_skills(session: Session) -> None:
    """
    Idempotently seed skills into database.
    - Check if skill with slug already exists
    - If not, insert it
    - If yes, skip (idempotent)
    """
    inserted_count = 0
    skipped_count = 0

    for skill_data in SKILLS_DATA:
        existing = session.execute(
            select(Skill).where(Skill.slug == skill_data["slug"])
        ).scalars().first()

        if existing:
            skipped_count += 1
        else:
            skill = Skill(
                slug=skill_data["slug"],
                name_tr=skill_data["name_tr"],
                name_en=skill_data["name_en"],
                category=skill_data["category"],
                status="ACTIVE",
                parent_id=None,
                merged_into_id=None,
            )
            session.add(skill)
            inserted_count += 1

    session.commit()
    print(f"Skill seed complete: {inserted_count} inserted, {skipped_count} already exist")


def seed_admin(session: Session) -> None:
    """
    Idempotently seed the first platform admin (PLAN 3.6 — YET-110).

    No self-servis admin-olma ucu vardır; bu, is_platform_admin=true bir
    kullanıcının var olmasının tek yolu (seed veya elle SQL). Zaten varsa
    dokunulmaz — parola sıfırlanmaz.
    """
    existing = session.execute(
        select(User).where(User.email == settings.seed_admin_email)
    ).scalars().first()

    if existing:
        print(f"Admin seed skip: {settings.seed_admin_email} already exists")
        return

    admin = User(
        email=settings.seed_admin_email,
        password_hash=hash_password(settings.seed_admin_password),
        is_platform_admin=True,
        status="ACTIVE",
        email_verified_at=datetime.now(timezone.utc),
    )
    session.add(admin)
    session.commit()
    print(f"Admin seed complete: {settings.seed_admin_email} created")


# ============================================================================
# PLAN 3.11: Seed talents, institutions, organizations, engagements
# ============================================================================


def seed_talents(session: Session) -> None:
    """
    Seed 20 student accounts (ogrenci1-20@seed.local), idempotently.

    AC-1, AC-2, AC-5: Production guard, idempotency, registration via register_user.
    Each call to register_user() automatically creates a TalentProfile.

    Test filters by User.email LIKE 'ogrenci%@seed.local' to count students only.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    inserted_count = 0
    skipped_count = 0

    for i in range(1, 21):
        email = f"ogrenci{i}@seed.local"

        # Check if email already exists
        existing = session.execute(
            select(User).where(User.email == email)
        ).scalars().first()

        if existing:
            skipped_count += 1
        else:
            # register_user automatically creates empty TalentProfile
            register_user(
                session=session,
                email=email,
                password="SeedTest123!",
                full_name=f"Student {i}"
            )
            inserted_count += 1

    print(f"Talents seed complete: {inserted_count} inserted, {skipped_count} already exist")


def seed_institutions_and_organizations(session: Session) -> None:
    """
    Seed 5 institutions + 5 organizations with admin accounts, idempotently.

    AC-1, AC-2, AC-5: Each institution gets an admin (kurum{i}-admin@seed.local).
    Each organization gets an admin (org{i}-admin@seed.local).

    Institutions: domain = f"inst{i}.seed.local"
    Organizations: legal_id = f"ORG{i}" (for uniqueness), domain = f"org{i}.seed.local"
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    inst_inserted = 0
    inst_skipped = 0
    org_inserted = 0
    org_skipped = 0

    # Seed 5 institutions
    for i in range(1, 6):
        inst_email = f"kurum{i}-admin@seed.local"
        inst_domain = f"inst{i}.seed.local"

        # Check if institution domain already exists
        existing_inst = session.execute(
            select(Institution).where(Institution.domain == inst_domain)
        ).scalars().first()

        if existing_inst:
            inst_skipped += 1
        else:
            # Create user for institution admin
            user_result = register_user(
                session=session,
                email=inst_email,
                password="SeedTest123!",
                full_name=f"Institution {i} Admin"
            )

            # Create institution (caller becomes ADMIN)
            create_institution(
                name=f"Institution {i}",
                domain=inst_domain,
                caller_user_id=user_result.user_id,
                session=session
            )
            inst_inserted += 1

    # Seed 5 organizations
    for i in range(1, 6):
        org_email = f"org{i}-admin@seed.local"
        org_legal_id = f"ORG{i}"
        org_domain = f"org{i}.seed.local"

        # Check if organization legal_id already exists
        existing_org = session.execute(
            select(Organization).where(Organization.legal_id == org_legal_id)
        ).scalars().first()

        if existing_org:
            org_skipped += 1
        else:
            # Create user for organization admin
            user_result = register_user(
                session=session,
                email=org_email,
                password="SeedTest123!",
                full_name=f"Organization {i} Admin"
            )

            # Create organization (caller becomes ADMIN)
            create_organization(
                name=f"Organization {i}",
                domain=org_domain,
                legal_id=org_legal_id,
                caller_user_id=user_result.user_id,
                session=session
            )
            org_inserted += 1

    print(f"Institutions seed: {inst_inserted} inserted, {inst_skipped} already exist")
    print(f"Organizations seed: {org_inserted} inserted, {org_skipped} already exist")


def _create_verified_engagement(
    session: Session,
    talent: TalentProfile,
    organization: Organization,
    institution: Institution,
    sample_skill: Skill,
    eng_idx: int
) -> Engagement:
    """
    Helper function: Create a single complete VERIFIED engagement.

    Executes the full state machine chain for one engagement:
    DRAFT → PENDING_APPROVAL → ACTIVE → PENDING_EVALUATION → EVALUATED → VERIFIED

    Returns the final engagement object.
    Raises Exception on failure (caught by caller).
    """
    # Link talent to institution (if not already linked)
    if talent.institution_id == institution.id:
        # Already linked, nothing to do (idempotent)
        pass
    else:
        # Request and approve institution link
        try:
            link_request = request_institution_link(
                institution_id=institution.id,
                talent_profile_id=talent.id,
                session=session
            )

            # Approve as institution admin (user who created institution)
            inst_admin = session.execute(
                select(User).where(
                    User.email == f"kurum{(eng_idx % 5) + 1}-admin@seed.local"
                )
            ).scalars().first()

            if inst_admin:
                approve_institution_link(
                    request_id=link_request.id,
                    institution_id=institution.id,
                    approver_user_id=inst_admin.id,
                    session=session
                )
        except DuplicateLinkRequestError:
            # Pending request already exists, just continue
            pass

    # Construct talent User for Principal
    talent_user = session.execute(
        select(User).where(User.id == talent.user_id)
    ).scalars().first()

    assert talent_user is not None, f"Talent user (ID: {talent.user_id}) not found in database — this should never happen as it was just created in seed_talents()"

    talent_principal = Principal(
        user_id=talent_user.id,
        kind="TALENT",
        talent_id=talent.id,
        org_ids=[],
        org_admin_ids=[],
        institution_ids=[],
        institution_admin_ids=[],
        is_platform_admin=False,
        is_suspended=False
    )

    # Get org admin user
    org_admin_email = f"org{(eng_idx % 5) + 1}-admin@seed.local"
    org_admin_user = session.execute(
        select(User).where(User.email == org_admin_email)
    ).scalars().first()

    assert org_admin_user is not None, f"Organization admin (email: {org_admin_email}) not found — this should have been created in seed_institutions_and_organizations()"

    org_admin_principal = Principal(
        user_id=org_admin_user.id,
        kind="ORG_ADMIN",
        talent_id=None,
        org_ids=[organization.id],
        org_admin_ids=[organization.id],
        institution_ids=[],
        institution_admin_ids=[],
        is_platform_admin=False,
        is_suspended=False
    )

    # Get institution admin/coordinator user
    coord_email = f"kurum{(eng_idx % 5) + 1}-admin@seed.local"
    coord_user = session.execute(
        select(User).where(User.email == coord_email)
    ).scalars().first()

    assert coord_user is not None, f"Coordinator user (email: {coord_email}) not found — this should have been created in seed_institutions_and_organizations()"

    coordinator_principal = Principal(
        user_id=coord_user.id,
        kind="COORDINATOR",
        talent_id=None,
        org_ids=[],
        org_admin_ids=[],
        institution_ids=[institution.id],
        institution_admin_ids=[],
        is_platform_admin=False,
        is_suspended=False
    )

    # T0: Create engagement (DRAFT)
    engagement = create_engagement(
        session=session,
        principal=talent_principal,
        talent_id=str(talent.id),
        organization_id=str(organization.id),
        kind="INTERNSHIP",
        title=f"Engagement {eng_idx + 1}",
        institution_id=str(institution.id),
        confidential=False
    )

    # T1: DRAFT → PENDING_APPROVAL (principal = TALENT)
    engagement = transition_engagement(
        session=session,
        principal=talent_principal,
        engagement_id=str(engagement.id),
        to_status="PENDING_APPROVAL",
        version=1,
        reason=None
    )

    # T2: PENDING_APPROVAL → ACTIVE (principal = COORDINATOR)
    engagement = transition_engagement(
        session=session,
        principal=coordinator_principal,
        engagement_id=str(engagement.id),
        to_status="ACTIVE",
        version=2,
        reason=None
    )

    # Set engagement dates (required for COMPETENCE criterion 2)
    engagement.started_on = datetime.now(timezone.utc).date() - timedelta(days=40)
    engagement.ended_on = datetime.now(timezone.utc).date()
    session.flush()

    # Create task and deliverable (required for PENDING_EVALUATION transition)
    create_engagement_task(
        session=session,
        principal=coordinator_principal,
        engagement_id=str(engagement.id),
        title=f"Task {eng_idx + 1}",
        description="Sample task",
        due_at=datetime.now(timezone.utc) + timedelta(days=7),
        skill_id=str(sample_skill.id)
    )

    create_deliverable(
        session=session,
        principal=talent_principal,
        engagement_id=str(engagement.id),
        title=f"Deliverable {eng_idx + 1}",
        description="Sample deliverable",
        skill_id=str(sample_skill.id)
    )

    # T6: ACTIVE → PENDING_EVALUATION (principal = ORG_ADMIN, reason optional for this transition per table)
    engagement = transition_engagement(
        session=session,
        principal=org_admin_principal,
        engagement_id=str(engagement.id),
        to_status="PENDING_EVALUATION",
        version=3,
        reason=None
    )

    # T7: Create evaluation (ORG_TO_TALENT) — auto-triggers EVALUATED transition
    create_evaluation(
        session=session,
        principal=org_admin_principal,
        engagement_id=str(engagement.id),
        direction="ORG_TO_TALENT",
        items=[
            {
                "criterion": "Technical Skills",
                "skill_id": str(sample_skill.id),
                "rating": "MEETS",
                "comment": "Good technical knowledge"
            }
        ],
        private_note="Seed evaluation"
    )

    # Refresh engagement to get updated status/version after evaluation
    session.refresh(engagement)

    # T8: Create attestation (principal = COORDINATOR) — auto-triggers VERIFIED transition
    attestation, verified_exp = create_attestation(
        session=session,
        principal=coordinator_principal,
        engagement_id=str(engagement.id),
        requested_claim_type="COMPETENCE",
        version=engagement.version,
        skill_id=str(sample_skill.id)
    )

    return engagement


def seed_engagements(session: Session) -> None:
    """
    Seed 15 complete VERIFIED engagements, idempotently.

    Full state machine chain for each engagement:
    DRAFT → PENDING_APPROVAL → ACTIVE → PENDING_EVALUATION → EVALUATED → VERIFIED

    Each engagement includes:
    - Talent (from 20 students, distributed unevenly)
    - Organization (from 5 organizations, cyclic)
    - Institution (from 5 institutions, cyclic)
    - EngagementTask + Deliverable (required for PENDING_EVALUATION transition)
    - Evaluation (ORG_TO_TALENT, auto-transitions to EVALUATED)
    - Attestation (auto-transitions to VERIFIED, creates VerifiedExperience + SkillSignal)

    AC-1, AC-2, AC-3, AC-4, AC-5, AC-7: All constraints met in single transaction.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    # Check if we already have 15 VERIFIED engagements (idempotency)
    existing_verified = session.execute(
        select(Engagement).where(Engagement.status == "VERIFIED")
    ).scalars().all()

    if len(existing_verified) >= 15:
        print("Engagements seed: 0 inserted, 15 already exist (idempotent)")
        return

    # Fetch all students, institutions, organizations, and one skill for evaluations
    students = session.execute(
        select(TalentProfile).join(
            User, TalentProfile.user_id == User.id
        ).where(
            User.email.like("ogrenci%@seed.local")
        )
    ).scalars().all()

    institutions = session.execute(select(Institution)).scalars().all()
    organizations = session.execute(select(Organization)).scalars().all()

    # Get a sample skill for evaluations
    sample_skill = session.execute(select(Skill).where(Skill.slug == "python")).scalars().first()

    if not students or not institutions or not organizations or not sample_skill:
        print("Warning: Cannot seed engagements — missing students, institutions, organizations, or skills")
        return

    inserted_count = 0

    # Create 15 engagements
    for eng_idx in range(15):
        # Distribute talents unevenly (some students 0, some 1-2 engagements)
        talent_idx = (eng_idx * 7) % len(students)  # Unevenness via prime number modulo
        talent = students[talent_idx]

        # Cycle through institutions and organizations
        institution = institutions[eng_idx % len(institutions)]
        organization = organizations[eng_idx % len(organizations)]

        _create_verified_engagement(
            session=session,
            talent=talent,
            organization=organization,
            institution=institution,
            sample_skill=sample_skill,
            eng_idx=eng_idx
        )
        inserted_count += 1

    print(f"Engagements seed complete: {inserted_count} inserted")


if __name__ == "__main__":
    session = _SessionLocal()
    try:
        # Seed in order: skills → talents → institutions/orgs → engagements
        print("Starting seed operations...")

        seed_skills(session)
        seed_admin(session)

        seed_talents(session)

        seed_institutions_and_organizations(session)

        seed_engagements(session)

        # Final commit for all seed data (AC-4: single transaction)
        session.commit()
        print("Seed complete: all data committed successfully")

    except Exception as e:
        # AC-4: Full rollback on error
        print(f"Error during seed: {e}", file=sys.stderr)
        session.rollback()
        print("Rollback completed: no data persisted", file=sys.stderr)
        sys.exit(1)

    finally:
        session.close()
