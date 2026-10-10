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

# frontend/messages/tr.json'daki calismalar.claimType ile aynı etiketler —
# e-posta backend'de üretildiği için burada da elle tutulur.
CLAIM_TYPE_LABELS = {
    "PARTICIPATION": "Katılım",
    "CONTRIBUTION": "Katkı",
    "COMPETENCE": "Yetkinlik",
    "CONDUCT": "Davranış",
}

ATTESTATION_CREATED_SUBJECT = "Yetkin360 - Çalışmanız doğrulandı"

# {claim_type_label}, {engagement_url}
ATTESTATION_CREATED_BODY = (
    "Çalışmanız için bir tanıklık verildi: {claim_type_label}.\n\n"
    "Detayları görmek için giriş yapın: {engagement_url}"
)

ENGAGEMENT_PENDING_APPROVAL_SUBJECT = "Yetkin360 - Onay bekleyen bir çalışma var"

# {engagement_url}
ENGAGEMENT_PENDING_APPROVAL_BODY = (
    "Kurumunuza bağlı bir öğrencinin çalışması onayınızı bekliyor.\n\n"
    "İncelemek için giriş yapın: {engagement_url}"
)

ORGANIZATION_VERIFICATION_APPROVED_SUBJECT = "Yetkin360 - Kuruluş doğrulamanız onaylandı"
ORGANIZATION_VERIFICATION_REJECTED_SUBJECT = "Yetkin360 - Kuruluş doğrulama başvurunuz reddedildi"

# {organization_name}, {login_url}
ORGANIZATION_VERIFICATION_APPROVED_BODY = (
    "{organization_name} kuruluşunun doğrulama başvurusu onaylandı.\n\n"
    "Güncel durumu görmek için giriş yapın: {login_url}"
)
ORGANIZATION_VERIFICATION_REJECTED_BODY = (
    "{organization_name} kuruluşunun doğrulama başvurusu reddedildi.\n\n"
    "Bilgilerinizi gözden geçirmek için giriş yapın: {login_url}"
)

# Şikayet (sikayet-backend): mails carry only a link — never the complaint text,
# the explanation or an attachment (AC-S13). {complaint_url}
COMPLAINT_EXPLANATION_REQUESTED_SUBJECT = "Yetkin360 - Hakkınızda bir şikayet için açıklama bekleniyor"
COMPLAINT_EXPLANATION_REQUESTED_BODY = (
    "Onayınızı bekleyen bir kayıtla ilgili platform yöneticisi sizden açıklama istedi.\n\n"
    "Açıklamanızı yazmak için giriş yapın: {complaint_url}"
)
COMPLAINT_ESCALATED_SUBJECT = "Yetkin360 - Yanıtsız kalan bir onay talebi size iletildi"
COMPLAINT_ESCALATED_BODY = (
    "Kurumunuzda/kuruluşunuzda yanıtsız kalan bir onay talebiyle ilgili şikayet size iletildi.\n\n"
    "Ayrıntıları görmek için giriş yapın: {complaint_url}"
)
COMPLAINT_CLOSED_SUBJECT = "Yetkin360 - Şikayetiniz sonuçlandı"
COMPLAINT_CLOSED_BODY = "Şikayetiniz sonuçlandı.\n\nSonucu görmek için giriş yapın: {complaint_url}"
