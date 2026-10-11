"""Create or repair the local .env from .env.example (called by the launchers).

Standard library only and Python 3.8+ compatible: it runs with whatever Python
the machine has, before the backend virtualenv exists.

- .env missing: copy .env.example and replace every ``DEGISTIR_*`` placeholder
  with a random value. The same placeholder always gets the same value, so
  POSTGRES_PASSWORD and the password inside DATABASE_URL stay in sync.
- .env present: only SEED_ADMIN_PASSWORD is repaired when it is empty, a
  placeholder or too short (scripts/seed.py refuses it and rolls the whole seed
  back). Other values are left alone: the database volume was initialised with
  them.

Secret values are never printed.
"""

from __future__ import annotations

import re
import secrets
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
EXAMPLE_FILE = ROOT / ".env.example"

PLACEHOLDER_PREFIX = "DEGISTIR_"
PLACEHOLDER = re.compile(r"DEGISTIR_[A-Za-z0-9_]*")
ADMIN_KEY = "SEED_ADMIN_PASSWORD"
MIN_ADMIN_PASSWORD_LENGTH = 12  # backend/scripts/seed.py

_ALNUM = string.ascii_letters + string.digits
# No 0/O, 1/l/I: the admin password is read off a terminal and typed by hand.
_READABLE = "abcdefghjkmnpqrstuvwxyz23456789"


def _random(alphabet: str, length: int) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(length))


def admin_password() -> str:
    groups = [_random(_READABLE, 4) for _ in range(3)]
    return "Demo-" + "-".join(groups)


def value_for(key: str) -> str:
    """Random value sized for the setting that uses it (URL-safe, no quoting needed)."""
    if key == ADMIN_KEY:
        return admin_password()
    if key == "SECRET_KEY":
        return _random(_ALNUM, 80)
    if key == "S3_ACCESS_KEY":
        return _random(_ALNUM, 20)  # MinIO root user
    if key == "S3_SECRET_KEY":
        return _random(_ALNUM, 40)  # MinIO root password
    return _random(_ALNUM, 32)


def _key_of(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def admin_password_is_usable(value: str) -> bool:
    return len(value) >= MIN_ADMIN_PASSWORD_LENGTH and not value.startswith(PLACEHOLDER_PREFIX)


def create_env(example_text: str) -> str:
    chosen: dict[str, str] = {}
    lines = []
    has_admin = False
    for line in example_text.splitlines():
        key = _key_of(line)
        if key is not None:
            if key == ADMIN_KEY:
                has_admin = True
                value = line.split("=", 1)[1].strip()
                if not admin_password_is_usable(value):
                    line = "%s=%s" % (ADMIN_KEY, admin_password())
            else:
                for token in PLACEHOLDER.findall(line):
                    if token not in chosen:
                        chosen[token] = value_for(key)
                    line = line.replace(token, chosen[token])
        lines.append(line)
    if not has_admin:
        lines += ["", "# Platform admin (scripts/seed.py)", "%s=%s" % (ADMIN_KEY, admin_password())]
    return "\n".join(lines) + "\n"


def repair_admin_password(env_text: str) -> str | None:
    """Return the fixed text, or None when nothing needed changing."""
    lines = env_text.splitlines()
    for index, line in enumerate(lines):
        if _key_of(line) == ADMIN_KEY:
            if admin_password_is_usable(line.split("=", 1)[1].strip()):
                return None
            lines[index] = "%s=%s" % (ADMIN_KEY, admin_password())
            return "\n".join(lines) + "\n"
    lines += ["", "# Platform admin (scripts/seed.py)", "%s=%s" % (ADMIN_KEY, admin_password())]
    return "\n".join(lines) + "\n"


def main() -> int:
    if not ENV_FILE.exists():
        if not EXAMPLE_FILE.exists():
            print("HATA: .env.example bulunamadı.", file=sys.stderr)
            return 1
        ENV_FILE.write_text(create_env(EXAMPLE_FILE.read_text(encoding="utf-8")), encoding="utf-8")
        print("created")
        return 0

    fixed = repair_admin_password(ENV_FILE.read_text(encoding="utf-8"))
    if fixed is None:
        print("ok")
    else:
        ENV_FILE.write_text(fixed, encoding="utf-8")
        print("admin-password-set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
