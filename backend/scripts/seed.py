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
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import _SessionLocal
from app.core.security import hash_password
from app.models import (
    Skill,
    User,
    TalentProfile,
    Institution,
    InstitutionMember,
    Organization,
    Engagement,
    VerifiedExperience,
    CertificateCheck,
    Deliverable,
    Evidence,
    PortfolioItem,
)
from app.models.base import uuid7_default
from app.services.auth import register_user
from app.services.institution import (
    create_institution,
    invite_member,
    request_institution_link,
    approve_institution_link,
    DuplicateLinkRequestError,
    AlreadyMemberError,
)
from app.services.organization import create_organization, set_verification_level
from app.services.engagement import (
    create_engagement,
    transition_engagement,
    create_engagement_task,
    create_deliverable,
)
from app.services.evaluation import create_evaluation
from app.services.attestation import create_attestation
from app.services.authorization import Principal
from app.services.talent import update_talent_profile


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


# PLAN 3.28: realistic (fictional) Turkish demo data — shown to the jury on every
# screen (panels, /v/[token] certificate, /p/[slug] public profile).

# (full_name, public_slug, department, study_year, headline, city) — ogrenci{i}@seed.local
STUDENTS_DATA = [
    ("Ayşe Yılmaz", "ayse-yilmaz", "Bilgisayar Mühendisliği", 4, "Backend geliştirmeye odaklı mühendislik öğrencisi", "İstanbul"),
    ("Mehmet Kaya", "mehmet-kaya", "Yazılım Mühendisliği", 3, "Web uygulamaları ve arayüz geliştirme", "İstanbul"),
    ("Zeynep Demir", "zeynep-demir", "Endüstri Mühendisliği", 4, "Veri analizi ve süreç iyileştirme", "İstanbul"),
    ("Emre Çelik", "emre-celik", "Elektrik-Elektronik Mühendisliği", 3, "Gömülü sistemler ve donanım prototipleme", "Kocaeli"),
    ("Elif Şahin", "elif-sahin", "Grafik Tasarım", 2, "Kullanıcı arayüzü ve marka tasarımı", "İstanbul"),
    ("Burak Arslan", "burak-arslan", "Bilgisayar Programcılığı", 2, "Frontend geliştirme meraklısı", "İstanbul"),
    ("Merve Koç", "merve-koc", "İşletme", 4, "Proje yönetimi ve operasyon", "İstanbul"),
    ("Can Aydın", "can-aydin", "Bilgisayar Mühendisliği", 4, "Bulut altyapısı ve DevOps", "İstanbul"),
    ("Selin Öztürk", "selin-ozturk", "İstatistik", 3, "Makine öğrenmesi ve veri bilimi", "İstanbul"),
    ("Ahmet Yıldız", "ahmet-yildiz", "Lojistik Yönetimi", 3, "Tedarik zinciri ve planlama", "Tekirdağ"),
    ("Deniz Aksoy", "deniz-aksoy", "Yönetim Bilişim Sistemleri", 3, "İş analizi ve raporlama", "İstanbul"),
    ("Ece Polat", "ece-polat", "İç Mimarlık", 4, "Mekân ve deneyim tasarımı", "İstanbul"),
    ("Oğuz Kurt", "oguz-kurt", "Bilgisayar Mühendisliği", 2, "Mobil uygulama geliştirme", "Bursa"),
    ("İrem Erdem", "irem-erdem", "Matematik", 3, "Algoritmalar ve veri analizi", "İstanbul"),
    ("Kaan Özdemir", "kaan-ozdemir", "Yazılım Mühendisliği", 4, "Siber güvenlik ve sistem yönetimi", "İstanbul"),
    ("Buse Çınar", "buse-cinar", "Endüstriyel Tasarım", 3, "Ürün tasarımı ve prototipleme", "İstanbul"),
    ("Yusuf Güneş", "yusuf-gunes", "Elektrik-Elektronik Mühendisliği", 4, "Yenilenebilir enerji sistemleri", "İstanbul"),
    ("Nisa Karaca", "nisa-karaca", "İşletme", 2, "Dijital pazarlama ve iletişim", "İstanbul"),
    ("Berk Doğan", "berk-dogan", "Bilgisayar Programcılığı", 2, "Python ile otomasyon", "İstanbul"),
    ("Melis Aydemir", "melis-aydemir", "Yönetim Bilişim Sistemleri", 4, "Veri tabanı ve iş zekâsı", "İstanbul"),
]

# (name, admin full_name, coordinator full_name) — kurum{i}-admin / kurum{i}-koordinator
INSTITUTIONS_DATA = [
    ("Galata Teknik Üniversitesi", "Nermin Aksoy", "Kerem Taşkın"),
    ("Sarıyer Teknoloji Enstitüsü", "Haluk Erdem", "Selin Karaca"),
    ("Kadıköy Uygulamalı Bilimler Üniversitesi", "Leyla Önal", "Burak Yalçın"),
    ("Levent İşletme ve Bilişim Yüksekokulu", "Cemal Arslan", "Deniz Kurt"),
    ("Moda Sanat ve Tasarım Akademisi", "Füsun Tekin", "Onur Çelik"),
]

# (name, admin full_name) — org{i}-admin
ORGANIZATIONS_DATA = [
    ("Lale Yazılım A.Ş.", "Murat Demirci"),
    ("Mavi Liman Lojistik", "Ebru Şahin"),
    ("Kuzey Enerji Teknolojileri", "Tolga Aydın"),
    ("Pusula Veri Analitiği", "Gizem Polat"),
    ("Atölye 34 Tasarım Stüdyosu", "Can Özkan"),
]

# One entry per seeded engagement (index = eng_idx): matches the student/organization
# picked in seed_engagements. (title, kind, skill_slug, task, deliverable, evaluation comment)
ENGAGEMENTS_DATA = [
    ("Backend Geliştirme Stajı", "INTERNSHIP", "fastapi", "Sipariş API'sinin uç noktalarını yazmak", "Sipariş servisi ve test raporu", "API tasarımı temiz, testleri eksiksiz."),
    ("Bulut Altyapısı ve DevOps Stajı", "INTERNSHIP", "docker", "Uygulamaları konteynerleştirmek", "Docker Compose kurulumu ve dağıtım belgesi", "Dağıtım süresini belirgin biçimde kısalttı."),
    ("Siber Güvenlik Değerlendirme Projesi", "SHORT_PROJECT", "cybersecurity", "İç ağ zafiyet taraması", "Zafiyet raporu ve iyileştirme planı", "Bulguları önceliklendirmesi çok yerindeydi."),
    ("Veri Paneli Arayüz Geliştirme", "PART_TIME", "react", "Müşteri paneli bileşenlerini geliştirmek", "Etkileşimli rapor paneli", "Arayüz kararlarını gerekçeleriyle sundu."),
    ("Görsel Arşiv Sınıflandırma Projesi", "CAPSTONE", "ml", "Arşiv görsellerini etiketleyen model eğitmek", "Sınıflandırma modeli ve doğruluk raporu", "Model doğruluğu beklentinin üzerinde."),
    ("Mobil Uygulama Arayüz Tasarımı", "SHORT_PROJECT", "problem-solving", "Kullanıcı akışlarını yeniden tasarlamak", "Tıklanabilir prototip", "Kullanıcı testlerinden doğru sonuçlar çıkardı."),
    ("Depo Süreçleri Veri Analizi", "INTERNSHIP", "data-analysis", "Toplama süreci verisini analiz etmek", "Süreç iyileştirme raporu", "Önerileri bekleme süresini azalttı."),
    ("Saha Ekipmanı Tedarik Planlaması", "INTERNSHIP", "project-mgmt", "Tedarik takvimini hazırlamak", "Tedarik planı ve risk tablosu", "Planlamayı düzenli ve zamanında yürüttü."),
    ("Enerji Tüketimi Tahmin Modeli", "CAPSTONE", "python", "Tüketim verisini temizlemek ve modellemek", "Tahmin modeli ve sunum", "Analizleri sağlam ve iyi belgelenmiş."),
    ("Etkileşimli Sergi Donanım Prototipi", "SHORT_PROJECT", "problem-solving", "Sensörlü sergi düzeneği kurmak", "Çalışan donanım prototipi", "Teknik sorunlara yaratıcı çözümler üretti."),
    ("Müşteri Destek Süreçleri İş Analizi", "PART_TIME", "data-analysis", "Destek kayıtlarını sınıflandırmak", "İş analizi dokümanı", "Paydaşlarla iletişimi güçlüydü."),
    ("Dijital Pazarlama ve İçerik Projesi", "SHORT_PROJECT", "communication", "Sosyal medya içerik takvimi hazırlamak", "Kampanya raporu", "Kampanya etkileşimi hedefi aştı."),
    ("Kurumsal Kimlik Yenileme Projesi", "SHORT_PROJECT", "presentation", "Marka rehberini güncellemek", "Kurumsal kimlik kılavuzu", "Sunumları net ve ikna ediciydi."),
    ("Ofis Deneyim Tasarımı Projesi", "SHORT_PROJECT", "teamwork", "Ortak çalışma alanını yeniden düzenlemek", "Mekân tasarım önerisi", "Ekiple uyum içinde çalıştı."),
    ("Sipariş Takip Otomasyonu", "INTERNSHIP", "python", "Sipariş takibini otomatikleştirmek", "Otomasyon betikleri ve kullanım kılavuzu", "Manuel iş yükünü önemli ölçüde azalttı."),
]

# Organizations raised to T3 by the platform admin (ORG{i} legal_id), so attestations
# can reach COMPETENCE. Mavi Liman (ORG2) stays T1 on purpose: the demo also shows
# how an unverified organization's record is flagged.
VERIFIED_ORG_LEGAL_IDS = ("ORG1", "ORG3", "ORG4")

# Public profile showcase (/p/ayse-yilmaz): extra verified engagements for ogrenci1,
# each with a different organization, kind, attested skill and task/deliverable skills.
# (org legal_id, spec as in ENGAGEMENTS_DATA, task skill slug, deliverable skill slug,
#  (ended N days ago, duration days))
SHOWCASE_STUDENT_EMAIL = "ogrenci1@seed.local"
SHOWCASE_ENGAGEMENTS = [
    (
        "ORG4",
        ("Sorgu Performansı İyileştirme Projesi", "SHORT_PROJECT", "postgresql",
         "Yavaş raporlama sorgularını analiz etmek", "İndeks önerileri ve ölçüm raporu",
         "Sorgu sürelerini ölçülebilir biçimde düşürdü."),
        "postgresql", "python", (120, 42),
    ),
    (
        "ORG3",
        ("Sayaç Verisi Toplama Servisi (Bitirme Projesi)", "CAPSTONE", "docker",
         "Servisi konteynerleştirip sahaya dağıtmak", "Çalışan servis, kurulum belgesi ve sunum",
         "Sahada sorunsuz çalışan bir servis teslim etti."),
        "git", "docker", (220, 110),
    ),
    (
        "ORG2",
        ("Depo Ekibi Raporlama Aracı", "PART_TIME", "teamwork",
         "Vardiya ekipleriyle ihtiyaçları toplamak", "Günlük rapor ekranı",
         "Ekiple uyumlu çalıştı, ihtiyaçları açıkça aktardı."),
        "communication", "react", (330, 21),
    ),
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


MIN_ADMIN_PASSWORD_LENGTH = 12
ADMIN_PASSWORD_PLACEHOLDER_PREFIX = "DEGISTIR_"


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

    # YET-229: never create the platform admin with an empty, placeholder or
    # short password. Checked after the skip above so existing databases are
    # unaffected. The password value is never printed.
    admin_password = settings.seed_admin_password
    if (
        len(admin_password) < MIN_ADMIN_PASSWORD_LENGTH
        or admin_password.startswith(ADMIN_PASSWORD_PLACEHOLDER_PREFIX)
    ):
        raise RuntimeError(
            "SEED_ADMIN_PASSWORD is missing, still a placeholder, or shorter than "
            f"{MIN_ADMIN_PASSWORD_LENGTH} characters; set a strong value in .env"
        )

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

    for i, (full_name, slug, department, study_year, headline, city) in enumerate(STUDENTS_DATA, start=1):
        email = f"ogrenci{i}@seed.local"

        # Check if email already exists
        existing = session.execute(
            select(User).where(User.email == email)
        ).scalars().first()

        if existing:
            skipped_count += 1
        else:
            # register_user automatically creates empty TalentProfile
            registered = register_user(
                session=session,
                email=email,
                password="SeedTest123!",
                full_name=full_name
            )
            profile = session.execute(
                select(TalentProfile).where(TalentProfile.user_id == registered.user_id)
            ).scalar_one()
            # Public profile so /p/[slug] works in the demo (PLAN 3.28, FE-02)
            update_talent_profile(
                profile,
                {
                    "department": department,
                    "study_year": study_year,
                    "headline": headline,
                    "city": city,
                    "visibility": "PUBLIC",
                    "public_slug": slug,
                },
                session,
            )
            inserted_count += 1

    print(f"Talents seed complete: {inserted_count} inserted, {skipped_count} already exist")


def _ensure_institution_coordinator(session: Session, index: int, inst_domain: str) -> None:
    """
    Ensure institution `index` has a real COORDINATOR member (kurum{i}-koordinator@seed.local).

    YET-190 / K3: only COORDINATOR members approve engagements and attest; the
    institution ADMIN does not. Idempotent, also repairs databases seeded earlier.
    """
    coord_email = f"kurum{index}-koordinator@seed.local"

    institution = session.execute(
        select(Institution).where(Institution.domain == inst_domain)
    ).scalars().first()
    assert institution is not None, f"Institution {inst_domain} must exist before adding its coordinator"

    coord_user = session.execute(
        select(User).where(User.email == coord_email)
    ).scalars().first()
    if coord_user is None:
        register_user(
            session=session,
            email=coord_email,
            password="SeedTest123!",
            full_name=INSTITUTIONS_DATA[index - 1][2],
        )

    try:
        invite_member(
            institution_id=institution.id,
            email=coord_email,
            role="COORDINATOR",
            session=session,
        )
    except AlreadyMemberError:
        pass  # idempotent re-run: the coordinator membership already exists


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
                full_name=INSTITUTIONS_DATA[i - 1][1]
            )

            # Create institution (caller becomes ADMIN)
            create_institution(
                name=INSTITUTIONS_DATA[i - 1][0],
                domain=inst_domain,
                caller_user_id=user_result.user_id,
                session=session
            )
            inst_inserted += 1

        _ensure_institution_coordinator(session, i, inst_domain)

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
                full_name=ORGANIZATIONS_DATA[i - 1][1]
            )

            # Create organization (caller becomes ADMIN)
            create_organization(
                name=ORGANIZATIONS_DATA[i - 1][0],
                domain=org_domain,
                legal_id=org_legal_id,
                caller_user_id=user_result.user_id,
                session=session
            )
            org_inserted += 1

    print(f"Institutions seed: {inst_inserted} inserted, {inst_skipped} already exist")
    print(f"Organizations seed: {org_inserted} inserted, {org_skipped} already exist")


def _link_to_institution(session: Session, talent: TalentProfile, institution: Institution) -> None:
    """Request + approve (as the institution's ADMIN) a talent's institution link. Idempotent."""
    if talent.institution_id == institution.id:
        return

    try:
        link_request = request_institution_link(
            institution_id=institution.id,
            talent_profile_id=talent.id,
            session=session
        )
    except DuplicateLinkRequestError:
        return  # pending request already exists

    inst_admin = session.execute(
        select(User)
        .join(InstitutionMember, InstitutionMember.user_id == User.id)
        .where(
            InstitutionMember.institution_id == institution.id,
            InstitutionMember.role == "ADMIN",
        )
    ).scalars().first()

    if inst_admin:
        approve_institution_link(
            request_id=link_request.id,
            institution_id=institution.id,
            approver_user_id=inst_admin.id,
            session=session
        )


def _create_verified_engagement(
    session: Session,
    talent: TalentProfile,
    organization: Organization,
    institution: Institution,
    skill: Skill,
    eng_idx: int,
    *,
    spec: tuple[str, str, str, str, str, str] | None = None,
    org_admin_email: str | None = None,
    task_skill: Skill | None = None,
    deliverable_skill: Skill | None = None,
    period: tuple[int, int] | None = None,
) -> Engagement:
    """
    Helper function: Create a single complete VERIFIED engagement.

    Executes the full state machine chain for one engagement:
    DRAFT → PENDING_APPROVAL → ACTIVE → PENDING_EVALUATION → EVALUATED → VERIFIED

    By default everything comes from ENGAGEMENTS_DATA[eng_idx]; the showcase seed
    passes its own spec (same tuple shape), org admin, task/deliverable skills and
    period (ended N days ago, lasting M days).

    Returns the final engagement object.
    Raises Exception on failure (caught by caller).
    """
    _link_to_institution(session, talent, institution)
    title, kind, _skill_slug, task_title, deliverable_title, comment = spec or ENGAGEMENTS_DATA[eng_idx]

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
    org_admin_email = org_admin_email or f"org{(eng_idx % 5) + 1}-admin@seed.local"
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

    # Get the institution's real COORDINATOR member (YET-190: admin does not approve/attest)
    coord_user = session.execute(
        select(User)
        .join(InstitutionMember, InstitutionMember.user_id == User.id)
        .where(
            InstitutionMember.institution_id == institution.id,
            InstitutionMember.role == "COORDINATOR",
        )
    ).scalars().first()

    assert coord_user is not None, f"Coordinator of institution {institution.id} not found — this should have been created in seed_institutions_and_organizations()"

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
        kind=kind,
        title=title,
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
    ended_days_ago, duration_days = period or (7 * eng_idx, 60 + 4 * eng_idx)
    engagement.ended_on = datetime.now(timezone.utc).date() - timedelta(days=ended_days_ago)
    engagement.started_on = engagement.ended_on - timedelta(days=duration_days)
    session.flush()

    # Create task and deliverable (required for PENDING_EVALUATION transition)
    create_engagement_task(
        session=session,
        principal=coordinator_principal,
        engagement_id=str(engagement.id),
        title=task_title,
        description=f"{title} kapsamında görev",
        due_at=datetime.now(timezone.utc) + timedelta(days=7),
        skill_id=str((task_skill or skill).id)
    )

    create_deliverable(
        session=session,
        principal=talent_principal,
        engagement_id=str(engagement.id),
        title=deliverable_title,
        description=f"{title} teslim dosyası",
        skill_id=str((deliverable_skill or skill).id)
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
                "criterion": "Teknik yetkinlik",
                "skill_id": str(skill.id),
                "rating": "MEETS",
                "comment": comment
            }
        ],
        private_note="Demo değerlendirmesi"
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
        skill_id=str(skill.id)
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

    # Fetch seed students (ogrenci1..20), institutions and organizations in seed order:
    # ENGAGEMENTS_DATA[eng_idx] is written for the student/organization picked below.
    student_rows = session.execute(
        select(User.email, TalentProfile).join(
            User, TalentProfile.user_id == User.id
        ).where(
            User.email.like("ogrenci%@seed.local")
        )
    ).all()
    students = [
        tp for _, tp in sorted(student_rows, key=lambda r: int(r[0].removeprefix("ogrenci").split("@")[0]))
    ]

    inst_by_domain = {
        inst.domain: inst
        for inst in session.execute(select(Institution).where(Institution.domain.like("inst%.seed.local"))).scalars()
    }
    institutions = [inst_by_domain[f"inst{i}.seed.local"] for i in range(1, 6) if f"inst{i}.seed.local" in inst_by_domain]
    org_by_legal_id = {
        org.legal_id: org
        for org in session.execute(select(Organization).where(Organization.legal_id.like("ORG%"))).scalars()
    }
    organizations = [org_by_legal_id[f"ORG{i}"] for i in range(1, 6) if f"ORG{i}" in org_by_legal_id]

    skills = {
        skill.slug: skill
        for skill in session.execute(
            select(Skill).where(Skill.slug.in_({row[2] for row in ENGAGEMENTS_DATA}))
        ).scalars()
    }

    if not students or not institutions or not organizations or len(skills) < len({row[2] for row in ENGAGEMENTS_DATA}):
        print("Warning: Cannot seed engagements — missing students, institutions, organizations, or skills")
        return

    inserted_count = 0

    # Create 15 engagements
    for eng_idx in range(len(ENGAGEMENTS_DATA)):
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
            skill=skills[ENGAGEMENTS_DATA[eng_idx][2]],
            eng_idx=eng_idx
        )
        inserted_count += 1

    # Students without an engagement still belong to an institution, so no demo
    # account lands on the "not linked to an institution" screen.
    for i, talent in enumerate(students):
        if talent.institution_id is None:
            _link_to_institution(session, talent, institutions[i % len(institutions)])

    print(f"Engagements seed complete: {inserted_count} inserted")


def seed_verified_organizations(session: Session) -> None:
    """
    Raise VERIFIED_ORG_LEGAL_IDS to T3 through the admin decision service, idempotently
    (same level again changes nothing). Runs before seed_engagements so their
    attestations are not downgraded for an unverified attestor organization.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    admin = session.execute(select(User).where(User.email == settings.seed_admin_email)).scalars().first()
    raised = 0
    for legal_id in VERIFIED_ORG_LEGAL_IDS:
        org = session.execute(select(Organization).where(Organization.legal_id == legal_id)).scalars().first()
        if org is None or org.verification_level == "T3":
            continue
        set_verification_level(session, org.id, "T3", admin.id if admin else None)
        raised += 1
    session.flush()
    print(f"Organization verification seed: {raised} raised to T3")


def seed_showcase_profile(session: Session) -> None:
    """
    Give the showcase student (ogrenci1, /p/ayse-yilmaz) extra verified engagements
    through the real state machine, so the public profile has several organizations,
    kinds, attested and evidenced skills. Idempotent per engagement title.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    talent = session.execute(
        select(TalentProfile).join(User, TalentProfile.user_id == User.id).where(User.email == SHOWCASE_STUDENT_EMAIL)
    ).scalars().first()
    if talent is None or talent.institution_id is None:
        print("Warning: showcase student or their institution missing — run seed_engagements first")
        return
    institution = session.get(Institution, talent.institution_id)
    assert institution is not None

    existing_titles = set(
        session.execute(select(Engagement.title).where(Engagement.talent_id == talent.id)).scalars().all()
    )
    inserted = 0
    for legal_id, spec, task_slug, deliverable_slug, period in SHOWCASE_ENGAGEMENTS:
        if spec[0] in existing_titles:
            continue
        org = session.execute(select(Organization).where(Organization.legal_id == legal_id)).scalars().first()
        skills = {
            sk.slug: sk
            for sk in session.execute(
                select(Skill).where(Skill.slug.in_({spec[2], task_slug, deliverable_slug}))
            ).scalars()
        }
        if org is None or len(skills) < len({spec[2], task_slug, deliverable_slug}):
            print(f"Warning: showcase engagement skipped (missing org/skill): {spec[0]}")
            continue
        _create_verified_engagement(
            session=session,
            talent=talent,
            organization=org,
            institution=institution,
            skill=skills[spec[2]],
            eng_idx=0,
            spec=spec,
            org_admin_email=f"{legal_id.lower()}-admin@seed.local",
            task_skill=skills[task_slug],
            deliverable_skill=skills[deliverable_slug],
            period=period,
        )
        inserted += 1
    print(f"Showcase profile seed: {inserted} engagements inserted")


# Showcase "Hakkımda" + certificate/work showcase for ogrenci1 (docs/arastirma-ogrenci-profili.md).
# No external links: a made-up verify/project URL would 404 in a live demo, so none are seeded.
SHOWCASE_ABOUT = (
    "Bilgisayar mühendisliği 4. sınıf öğrencisiyim. Backend geliştirme ve veritabanı performansıyla "
    "ilgileniyorum; ölçerek iyileştirmeyi ve yaptığımı açık bir dille belgelemeyi seviyorum.\n"
    "Şu an FastAPI ve PostgreSQL üzerine çalışıyorum, boş zamanlarımda kampüs projelerine katkı veriyorum."
)
SHOWCASE_CONFIRMED_ENGAGEMENT = ("ORG4", "Sorgu Performansı İyileştirme Projesi")
SHOWCASE_SELF_DECLARED = [
    # (kind, title, issuer, issued_on, credential_id, show_on_profile)
    ("CERTIFICATE", "SQL Temelleri", "Udemy", date(2026, 2, 1), "UC-7F3K2M9Q", True),
    ("WORK", "Kampüs etkinlik takvimi (kişisel proje)", "Öğrenci kulübü", date(2026, 4, 1), None, True),
    ("CERTIFICATE", "İngilizce B2", "Dil okulu", date(2025, 6, 1), None, False),
]


def seed_showcase_portfolio(session: Session) -> None:
    """
    Fill the showcase student's "Hakkımda" and certificate showcase (idempotent).

    - about text, only when empty
    - one certificate uploaded inside a verified engagement, with a certificate
      check CONFIRMED by that organization's admin → "Koordinatör onaylı" card.
      The evidence row is metadata only (no object in storage); it stays PRIVATE.
    - self-declared items, one of them with consent off (not on the public page)
    Skipped entirely when the student already has live (not deleted) portfolio items.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    talent = session.execute(
        select(TalentProfile).join(User, TalentProfile.user_id == User.id).where(User.email == SHOWCASE_STUDENT_EMAIL)
    ).scalars().first()
    if talent is None:
        print("Warning: showcase student missing — run seed_talents first")
        return
    if not talent.about:
        talent.about = SHOWCASE_ABOUT

    has_items = session.execute(
        select(PortfolioItem.id).where(PortfolioItem.talent_id == talent.id, PortfolioItem.deleted_at.is_(None))
    ).first()
    if has_items:
        print("Showcase portfolio seed: already present, skipped")
        return

    legal_id, engagement_title = SHOWCASE_CONFIRMED_ENGAGEMENT
    deliverable = session.execute(
        select(Deliverable)
        .join(Engagement, Deliverable.engagement_id == Engagement.id)
        .where(Engagement.talent_id == talent.id, Engagement.title == engagement_title)
    ).scalars().first()
    coordinator = session.execute(
        select(User).where(User.email == f"{legal_id.lower()}-admin@seed.local")
    ).scalars().first()
    inserted = 0
    if deliverable is not None and coordinator is not None:
        evidence = Evidence(
            owner_talent_id=talent.id,
            deliverable_id=deliverable.id,
            kind="CERTIFICATE",
            storage_key=f"evidence/{talent.id}/{uuid7_default()}.pdf",
            mime_type="application/pdf",
            size_bytes=48_213,
            scan_status="CLEAN",
        )
        session.add(evidence)
        session.flush()
        decided_at = datetime.now(timezone.utc) - timedelta(days=100)
        session.add(
            CertificateCheck(
                evidence_id=evidence.id,
                requested_by_talent_at=decided_at - timedelta(days=2),
                status="DONE",
                provider="COURSERA",
                credential_id="SEED-PGPERF-2026",
                verify_url=None,
                name_match=True,
                decision="CONFIRMED",
                decided_by_user_id=coordinator.id,
                decided_at=decided_at,
            )
        )
        session.add(
            PortfolioItem(
                talent_id=talent.id,
                kind="CERTIFICATE",
                title="PostgreSQL ile Sorgu Optimizasyonu",
                issued_on=date(2026, 5, 1),
                evidence_id=evidence.id,
                show_on_profile=True,
            )
        )
        inserted += 1
    else:
        print("Warning: confirmed showcase certificate skipped (engagement or coordinator missing)")

    for kind, title, issuer, issued_on, credential_id, show in SHOWCASE_SELF_DECLARED:
        session.add(
            PortfolioItem(
                talent_id=talent.id,
                kind=kind,
                title=title,
                issuer=issuer,
                issued_on=issued_on,
                credential_id=credential_id,
                show_on_profile=show,
            )
        )
        inserted += 1
    session.flush()
    print(f"Showcase portfolio seed: {inserted} items inserted")


def seed_public_experiences(session: Session) -> int:
    """
    Make every seed student's verified experiences PUBLIC so /p/[slug] and /v/[token]
    work in the demo (they are created PRIVATE). visibility is the only mutable
    column of verified_experiences. Returns rows updated.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    seed_talent_ids = (
        select(TalentProfile.id)
        .join(User, TalentProfile.user_id == User.id)
        .where(User.email.like("ogrenci%@seed.local"))
    )
    result = session.execute(
        update(VerifiedExperience)
        .where(VerifiedExperience.talent_id.in_(seed_talent_ids))
        .where(VerifiedExperience.visibility != "PUBLIC")
        .values(visibility="PUBLIC")
    )
    count = result.rowcount  # type: ignore[attr-defined]
    print(f"Public experiences seed: {count} made PUBLIC")
    return count


def seed_verify_users(session: Session) -> int:
    """
    YET-196: write endpoints require a verified e-mail, and seed users never
    receive their verification mail. Mark every @seed.local user verified so the
    demo accounts can write. Also repairs seed users created before this existed
    (the seed is idempotent and skips existing users). Returns rows updated.
    """
    if settings.environment == "production":
        raise RuntimeError("Seed script cannot run in production environment")

    result = session.execute(
        update(User)
        .where(User.email.like("%@seed.local"))
        .where(User.email_verified_at.is_(None))
        .values(email_verified_at=datetime.now(timezone.utc))
    )
    count = result.rowcount  # type: ignore[attr-defined]
    print(f"Seed users verified: {count} updated")
    return count


if __name__ == "__main__":
    session = _SessionLocal()
    try:
        # Seed in order: skills → talents → institutions/orgs → engagements
        print("Starting seed operations...")

        seed_skills(session)
        seed_admin(session)

        seed_talents(session)

        seed_institutions_and_organizations(session)

        seed_verified_organizations(session)

        seed_engagements(session)

        seed_showcase_profile(session)

        seed_showcase_portfolio(session)

        seed_public_experiences(session)

        seed_verify_users(session)

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
