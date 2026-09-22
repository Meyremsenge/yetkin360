"""
Skill taxonomy seed script (YET-10).

Populates database with ~30-50 representative skills across 5 categories.

Usage: python -m scripts.seed

WARNING: This script is intended for development/testing only.
DO NOT run in production without careful consideration.
"""

import sys
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import _SessionLocal
from app.models import Skill


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


if __name__ == "__main__":
    session = _SessionLocal()
    try:
        seed_skills(session)
    except Exception as e:
        print(f"Error during seed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()
