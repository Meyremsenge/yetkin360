"""
Turkish e-mail texts, kept out of the worker code (CLAUDE.md: user-facing text
lives in constant files). Only the organization-invite mail lives here so far;
the verify/reset mails still carry their text in app/workers/outbox_worker.py.
"""

ORGANIZATION_INVITE_SUBJECT = "Yetkin360 - Bir kuruluşa eklendiniz"

# Shown instead of the raw role code (ADMIN / MEMBER).
ORGANIZATION_ROLE_LABELS = {
    "ADMIN": "yönetici",
    "MEMBER": "üye",
}

# {organization_name}, {role_label}, {login_url}
ORGANIZATION_INVITE_BODY = (
    "{organization_name} kuruluşuna {role_label} olarak eklendiniz.\n\n"
    "Kuruluş bilgilerinizi görmek için giriş yapın: {login_url}"
)
