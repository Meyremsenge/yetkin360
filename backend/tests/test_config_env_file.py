"""S0: YETKIN360_ENV_FILE points settings at an env file outside the checkout (git worktrees).

Only paths are compared; no env file is opened here.
"""

from pathlib import Path

from app.core.config import REPO_ROOT, Settings, resolve_env_file


def test_env_file_defaults_to_repo_root(monkeypatch):
    monkeypatch.delenv("YETKIN360_ENV_FILE", raising=False)
    assert resolve_env_file() == REPO_ROOT / ".env"


def test_env_file_empty_override_falls_back_to_repo_root(monkeypatch):
    monkeypatch.setenv("YETKIN360_ENV_FILE", "")
    assert resolve_env_file() == REPO_ROOT / ".env"


def test_env_file_override_is_used(monkeypatch, tmp_path):
    target = tmp_path / "elsewhere" / ".env"
    monkeypatch.setenv("YETKIN360_ENV_FILE", str(target))
    assert resolve_env_file() == target


def test_settings_model_config_uses_resolver():
    # Settings is built at import time with the resolver's value for this process.
    assert Path(Settings.model_config["env_file"]) == resolve_env_file()
