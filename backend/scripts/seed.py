"""
Seed script for ~150 skill taxonomy records (LANGUAGE, FRAMEWORK, TOOL, DOMAIN, SOFT categories).

Usage: python -m scripts.seed
Or programmatically: from scripts.seed import main; main(session=session)

Accepts optional session parameter for testing. If None, creates its own session and commits.
Uses ON CONFLICT (slug) DO NOTHING for idempotent insertion.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Skill


# ~150 skill taxonomy data (curated, realistic, across 5 categories)
SKILL_TAXONOMY = [
    # LANGUAGE (programming languages)
    ("python", "Python", "Python", "LANGUAGE"),
    ("javascript", "JavaScript", "JavaScript", "LANGUAGE"),
    ("typescript", "TypeScript", "TypeScript", "LANGUAGE"),
    ("java", "Java", "Java", "LANGUAGE"),
    ("csharp", "C#", "C#", "LANGUAGE"),
    ("cpp", "C++", "C++", "LANGUAGE"),
    ("c", "C", "C", "LANGUAGE"),
    ("ruby", "Ruby", "Ruby", "LANGUAGE"),
    ("php", "PHP", "PHP", "LANGUAGE"),
    ("go", "Go", "Go", "LANGUAGE"),
    ("rust", "Rust", "Rust", "LANGUAGE"),
    ("kotlin", "Kotlin", "Kotlin", "LANGUAGE"),
    ("swift", "Swift", "Swift", "LANGUAGE"),
    ("objc", "Objective-C", "Objective-C", "LANGUAGE"),
    ("scala", "Scala", "Scala", "LANGUAGE"),
    ("haskell", "Haskell", "Haskell", "LANGUAGE"),
    ("elixir", "Elixir", "Elixir", "LANGUAGE"),
    ("erlang", "Erlang", "Erlang", "LANGUAGE"),
    ("perl", "Perl", "Perl", "LANGUAGE"),
    ("lua", "Lua", "Lua", "LANGUAGE"),
    ("r", "R", "R", "LANGUAGE"),
    ("matlab", "MATLAB", "MATLAB", "LANGUAGE"),
    ("sql", "SQL", "SQL", "LANGUAGE"),
    ("bash", "Bash", "Bash", "LANGUAGE"),
    ("powershell", "PowerShell", "PowerShell", "LANGUAGE"),

    # FRAMEWORK (web, mobile, desktop frameworks)
    ("react", "React", "React", "FRAMEWORK"),
    ("vue", "Vue.js", "Vue.js", "FRAMEWORK"),
    ("angular", "Angular", "Angular", "FRAMEWORK"),
    ("svelte", "Svelte", "Svelte", "FRAMEWORK"),
    ("nextjs", "Next.js", "Next.js", "FRAMEWORK"),
    ("nuxtjs", "Nuxt.js", "Nuxt.js", "FRAMEWORK"),
    ("gatsby", "Gatsby", "Gatsby", "FRAMEWORK"),
    ("django", "Django", "Django", "FRAMEWORK"),
    ("flask", "Flask", "Flask", "FRAMEWORK"),
    ("fastapi", "FastAPI", "FastAPI", "FRAMEWORK"),
    ("spring", "Spring", "Spring", "FRAMEWORK"),
    ("springboot", "Spring Boot", "Spring Boot", "FRAMEWORK"),
    ("laravel", "Laravel", "Laravel", "FRAMEWORK"),
    ("symfony", "Symfony", "Symfony", "FRAMEWORK"),
    ("rails", "Ruby on Rails", "Ruby on Rails", "FRAMEWORK"),
    ("express", "Express.js", "Express.js", "FRAMEWORK"),
    ("nestjs", "NestJS", "NestJS", "FRAMEWORK"),
    ("aspnet", "ASP.NET", "ASP.NET", "FRAMEWORK"),
    ("aspnetcore", "ASP.NET Core", "ASP.NET Core", "FRAMEWORK"),
    ("gin", "Gin", "Gin", "FRAMEWORK"),
    ("echo", "Echo", "Echo", "FRAMEWORK"),
    ("dotnet", ".NET", ".NET", "FRAMEWORK"),
    ("dotnetframework", ".NET Framework", ".NET Framework", "FRAMEWORK"),
    ("electron", "Electron", "Electron", "FRAMEWORK"),
    ("tauri", "Tauri", "Tauri", "FRAMEWORK"),
    ("flutter", "Flutter", "Flutter", "FRAMEWORK"),
    ("reactnative", "React Native", "React Native", "FRAMEWORK"),
    ("swiftui", "SwiftUI", "SwiftUI", "FRAMEWORK"),
    ("jetpackcompose", "Jetpack Compose", "Jetpack Compose", "FRAMEWORK"),

    # TOOL (libraries, build tools, databases, CI/CD, deployment)
    ("numpy", "NumPy", "NumPy", "TOOL"),
    ("pandas", "Pandas", "Pandas", "TOOL"),
    ("tensorflow", "TensorFlow", "TensorFlow", "TOOL"),
    ("pytorch", "PyTorch", "PyTorch", "TOOL"),
    ("scikit-learn", "scikit-learn", "scikit-learn", "TOOL"),
    ("matplotlib", "Matplotlib", "Matplotlib", "TOOL"),
    ("junit", "JUnit", "JUnit", "TOOL"),
    ("jest", "Jest", "Jest", "TOOL"),
    ("pytest", "Pytest", "Pytest", "TOOL"),
    ("rspec", "RSpec", "RSpec", "TOOL"),
    ("mocha", "Mocha", "Mocha", "TOOL"),
    ("webpack", "Webpack", "Webpack", "TOOL"),
    ("vite", "Vite", "Vite", "TOOL"),
    ("parcel", "Parcel", "Parcel", "TOOL"),
    ("gulp", "Gulp", "Gulp", "TOOL"),
    ("grunt", "Grunt", "Grunt", "TOOL"),
    ("npm", "npm", "npm", "TOOL"),
    ("yarn", "Yarn", "Yarn", "TOOL"),
    ("pnpm", "pnpm", "pnpm", "TOOL"),
    ("docker", "Docker", "Docker", "TOOL"),
    ("kubernetes", "Kubernetes", "Kubernetes", "TOOL"),
    ("postgresql", "PostgreSQL", "PostgreSQL", "TOOL"),
    ("mysql", "MySQL", "MySQL", "TOOL"),
    ("mongodb", "MongoDB", "MongoDB", "TOOL"),
    ("redis", "Redis", "Redis", "TOOL"),
    ("elasticsearch", "Elasticsearch", "Elasticsearch", "TOOL"),
    ("rabbitmq", "RabbitMQ", "RabbitMQ", "TOOL"),
    ("kafka", "Kafka", "Kafka", "TOOL"),
    ("graphql", "GraphQL", "GraphQL", "TOOL"),
    ("rest", "REST API", "REST API", "TOOL"),
    ("grpc", "gRPC", "gRPC", "TOOL"),
    ("git", "Git", "Git", "TOOL"),
    ("jenkins", "Jenkins", "Jenkins", "TOOL"),
    ("gitlab-ci", "GitLab CI", "GitLab CI", "TOOL"),
    ("github-actions", "GitHub Actions", "GitHub Actions", "TOOL"),
    ("circleci", "CircleCI", "CircleCI", "TOOL"),
    ("aws", "AWS", "AWS", "TOOL"),
    ("azure", "Azure", "Azure", "TOOL"),
    ("gcp", "Google Cloud Platform", "Google Cloud Platform", "TOOL"),
    ("heroku", "Heroku", "Heroku", "TOOL"),
    ("vercel", "Vercel", "Vercel", "TOOL"),
    ("netlify", "Netlify", "Netlify", "TOOL"),
    ("terraform", "Terraform", "Terraform", "TOOL"),
    ("ansible", "Ansible", "Ansible", "TOOL"),
    ("prometheus", "Prometheus", "Prometheus", "TOOL"),
    ("grafana", "Grafana", "Grafana", "TOOL"),
    ("datadog", "Datadog", "Datadog", "TOOL"),
    ("sentry", "Sentry", "Sentry", "TOOL"),
    ("postman", "Postman", "Postman", "TOOL"),
    ("swagger", "Swagger", "Swagger", "TOOL"),
    ("jira", "Jira", "Jira", "TOOL"),
    ("confluence", "Confluence", "Confluence", "TOOL"),
    ("slack", "Slack", "Slack", "TOOL"),
    ("git-github", "GitHub", "GitHub", "TOOL"),
    ("git-gitlab", "GitLab", "GitLab", "TOOL"),
    ("bitbucket", "Bitbucket", "Bitbucket", "TOOL"),
    ("figma", "Figma", "Figma", "TOOL"),
    ("sketch", "Sketch", "Sketch", "TOOL"),
    ("adobe-xd", "Adobe XD", "Adobe XD", "TOOL"),

    # DOMAIN (vertical/industry expertise)
    ("fintech", "Fintech", "Fintech", "DOMAIN"),
    ("ecommerce", "E-Commerce", "E-Commerce", "DOMAIN"),
    ("healthtech", "HealthTech", "HealthTech", "DOMAIN"),
    ("edtech", "EdTech", "EdTech", "DOMAIN"),
    ("proptech", "PropTech", "PropTech", "DOMAIN"),
    ("insurtech", "InsurTech", "InsurTech", "DOMAIN"),
    ("biotech", "BioTech", "BioTech", "DOMAIN"),
    ("iot", "IoT", "IoT", "DOMAIN"),
    ("ai-ml", "AI/Machine Learning", "AI/Machine Learning", "DOMAIN"),
    ("blockchain", "Blockchain", "Blockchain", "DOMAIN"),
    ("gaming", "Game Development", "Game Development", "DOMAIN"),
    ("saas", "SaaS", "SaaS", "DOMAIN"),
    ("agtech", "AgTech", "AgTech", "DOMAIN"),
    ("legaltech", "LegalTech", "LegalTech", "DOMAIN"),
    ("hrtech", "HRTech", "HRTech", "DOMAIN"),
    ("government", "Government Tech", "Government Tech", "DOMAIN"),
    ("manufacturing", "Manufacturing", "Manufacturing", "DOMAIN"),
    ("logistics", "Logistics", "Logistics", "DOMAIN"),
    ("media", "Media & Broadcasting", "Media & Broadcasting", "DOMAIN"),
    ("automotive", "Automotive", "Automotive", "DOMAIN"),

    # SOFT (soft skills / transferable skills)
    ("leadership", "Liderlik", "Leadership", "SOFT"),
    ("communication", "İletişim", "Communication", "SOFT"),
    ("teamwork", "Takım Çalışması", "Teamwork", "SOFT"),
    ("problem-solving", "Problem Çözme", "Problem Solving", "SOFT"),
    ("critical-thinking", "Eleştirel Düşünme", "Critical Thinking", "SOFT"),
    ("creativity", "Yaratıcılık", "Creativity", "SOFT"),
    ("adaptability", "Uyum Sağlayabilirlik", "Adaptability", "SOFT"),
    ("project-management", "Proje Yönetimi", "Project Management", "SOFT"),
    ("time-management", "Zaman Yönetimi", "Time Management", "SOFT"),
    ("negotiation", "Müzakere", "Negotiation", "SOFT"),
    ("public-speaking", "Halk Konuşması", "Public Speaking", "SOFT"),
    ("presentation", "Sunum Yapma", "Presentation", "SOFT"),
    ("documentation", "Belgelendirme", "Documentation", "SOFT"),
    ("mentoring", "Mentorluk", "Mentoring", "SOFT"),
    ("training", "Eğitim Verme", "Training", "SOFT"),
    ("customer-service", "Müşteri Hizmetleri", "Customer Service", "SOFT"),
    ("conflict-resolution", "Çatışma Çözümü", "Conflict Resolution", "SOFT"),
    ("empathy", "Empati", "Empathy", "SOFT"),
    ("strategic-thinking", "Stratejik Düşünme", "Strategic Thinking", "SOFT"),
    ("innovation", "İnovasyon", "Innovation", "SOFT"),
]


def main(session: Session | None = None) -> dict[str, int]:
    """
    Seed ~150 skills into the database.

    Args:
        session: Optional SQLAlchemy Session. If None, creates its own session.

    Returns:
        dict with keys: 'created', 'skipped', 'total' (informational, not tested by name).

    Behavior:
        - If session is None: creates a new session, commits, closes.
        - If session is provided: uses it, does NOT commit/close (caller manages transaction).
        - Uses ON CONFLICT (slug) DO NOTHING for idempotent insertion.
        - Each record: slug (UNIQUE, CITEXT), name_tr, name_en, category.
        - All inserted skills default to status=ACTIVE (DB server_default).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    close_session = False
    if session is None:
        # Create a new session for standalone execution
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        close_session = True

    try:
        # Prepare records as dicts for bulk insert
        records = [
            {
                "slug": slug,
                "name_tr": name_tr,
                "name_en": name_en,
                "category": category,
            }
            for slug, name_tr, name_en, category in SKILL_TAXONOMY
        ]

        # Count existing skills before insertion
        from sqlalchemy import text
        before_count = session.execute(text("SELECT COUNT(*) FROM skills")).scalar()

        # Bulk insert with ON CONFLICT (slug) DO NOTHING for idempotency
        # PostgreSQL dialect: use pg_insert for ON CONFLICT support
        stmt = pg_insert(Skill).values(records).on_conflict_do_nothing(index_elements=["slug"])
        session.execute(stmt)
        if close_session:
            session.commit()

        # Count after insertion
        after_count = session.execute(text("SELECT COUNT(*) FROM skills")).scalar()

        created = after_count - before_count
        skipped = len(SKILL_TAXONOMY) - created

        print(f"Seed completed: {created} new skills added, {skipped} skipped (duplicates).")

        return {
            "created": created,
            "skipped": skipped,
            "total": len(SKILL_TAXONOMY),
        }

    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    main()
