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

COMPLAINT_OPENED_SUBJECT = "Yetkin360 - Bir çalışma için şikayet açıldı"

# {engagement_url}
COMPLAINT_OPENED_BODY = (
    "Kuruluşunuzdaki bir çalışma için öğrenci, onay sürecinin ilerlemediğini bildiren bir şikayet açtı.\n\n"
    "Bekleyen bir görev onayı, değerlendirme ya da doğrulama varsa lütfen tamamlayın: {engagement_url}\n\n"
    "Şikayeti platform yöneticisi inceleyecek. Onay vermemenizin bir gerekçesi varsa "
    "bu e-postayı yanıtlayarak bildirin."
)

COMPLAINT_RESOLVED_SUBJECT = "Yetkin360 - Şikayetiniz karara bağlandı"

# {outcome_label}, {engagement_url}
COMPLAINT_RESOLVED_BODY = (
    "Açtığınız şikayet incelendi. Sonuç: {outcome_label}.\n\n"
    "Ayrıntılar için çalışmanızı açın: {engagement_url}"
)

COMPLAINT_OUTCOME_LABELS = {
    "UPHELD": "şikayetiniz haklı bulundu",
    "DISMISSED": "şikayetiniz kapatıldı",
}

ENGAGEMENT_PENDING_APPROVAL_SUBJECT = "Yetkin360 - Onay bekleyen bir çalışma var"

# {engagement_url}
ENGAGEMENT_PENDING_APPROVAL_BODY = (
    "Kurumunuza bağlı bir öğrencinin çalışması onayınızı bekliyor.\n\n"
    "İncelemek için giriş yapın: {engagement_url}"
)
