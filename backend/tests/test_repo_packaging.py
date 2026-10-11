"""
Repo packaging regression tests — documentation and setup integrity.
Tests verify that README installation steps are current, .env handling is documented,
and security scan baseline exists (automated subset of AC-1, AC-2, AC-3, AC-7).
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_exists_at_repo_root():
    """AC-1, AC-3: .env.example file must exist at repo root for installation instructions to work."""
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), f".env.example not found at {env_example}"
    assert env_example.is_file(), f".env.example exists but is not a file at {env_example}"


def test_readme_does_not_claim_env_example_missing():
    """AC-3: README.md must not contain stale instruction claiming .env.example is missing.
    This test currently FAILS (red) because README.md still says 'henüz repoda yok',
    reflecting the intended state before the fix commit that will correct the text."""
    readme = REPO_ROOT / "README.md"
    assert readme.exists(), f"README.md not found at {readme}"

    readme_text = readme.read_text(encoding="utf-8")
    stale_phrase = "henüz repoda yok"
    assert stale_phrase not in readme_text, (
        f"README.md contains stale instruction '{stale_phrase}' — "
        f".env.example file exists at repo root (docs/PLAN.md 0.9 complete), "
        f"but README still directs users to docs/ENV.md instead"
    )


def test_secrets_baseline_exists():
    """AC-2, AC-7: .secrets.baseline must exist for detect-secrets integration."""
    baseline = REPO_ROOT / ".secrets.baseline"
    assert baseline.exists(), f".secrets.baseline not found at {baseline}"
    assert baseline.is_file(), f".secrets.baseline exists but is not a file at {baseline}"


def test_env_file_is_gitignored():
    """AC-1: .env file (without suffix) must be in .gitignore to prevent secret leaks.
    Exact match ensures .env.example is not accidentally matched."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), f".gitignore not found at {gitignore}"

    gitignore_lines = gitignore.read_text(encoding="utf-8").split("\n")
    gitignore_lines = [line.strip() for line in gitignore_lines if line.strip()]

    assert ".env" in gitignore_lines, (
        ".env not found as a line in .gitignore — "
        "actual .env files would be tracked and secrets leaked"
    )


def test_readme_lists_required_env_example_step():
    """AC-1: README installation instructions must reference copying .env.example to .env."""
    readme = REPO_ROOT / "README.md"
    assert readme.exists(), f"README.md not found at {readme}"

    readme_text = readme.read_text(encoding="utf-8")
    step_text = "cp .env.example .env"
    assert step_text in readme_text, (
        f"README.md does not list step '{step_text}' — "
        f"users following instructions will not know to create .env from example"
    )
