# code_diff — ogrenci-profili-hakkimda-sertifika (backend)

```diff
diff --git a/backend/alembic/versions/a7c3e9d1f2b4_talent_about_ve_portfolio_items.py b/backend/alembic/versions/a7c3e9d1f2b4_talent_about_ve_portfolio_items.py
new file mode 100644
index 0000000..2dace3b
--- /dev/null
+++ b/backend/alembic/versions/a7c3e9d1f2b4_talent_about_ve_portfolio_items.py
@@ -0,0 +1,77 @@
+"""talent_profiles.about ve portfolio_items tablosu eklendi
+
+docs/arastirma-ogrenci-profili.md §4: "Hakkımda" (kendi beyanı, en fazla 1000
+karakter) ve çalışma içi/dışı sertifika/çalışma vitrini. Yalnız ekleme — geriye uyumlu.
+
+Revision ID: a7c3e9d1f2b4
+Revises: 237dbae3e129
+Create Date: 2026-10-10 16:00:00.000000
+
+"""
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+
+
+revision: str = 'a7c3e9d1f2b4'
+down_revision: Union[str, None] = '237dbae3e129'
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    op.add_column('talent_profiles', sa.Column('about', sa.Text(), nullable=True))
+    op.create_check_constraint(
+        'ck_talent_profiles_about_length',
+        'talent_profiles',
+        'about IS NULL OR char_length(about) <= 1000',
+    )
+
+    op.create_table(
+        'portfolio_items',
+        sa.Column('id', sa.UUID(), nullable=False),
+        sa.Column('talent_id', sa.UUID(), nullable=False),
+        sa.Column('kind', sa.String(length=20), nullable=False),
+        sa.Column('title', sa.String(length=120), nullable=False),
+        sa.Column('issuer', sa.String(length=120), nullable=True),
+        sa.Column('issued_on', sa.Date(), nullable=True),
+        sa.Column('credential_id', sa.String(length=100), nullable=True),
+        sa.Column('external_url', sa.String(length=500), nullable=True),
+        sa.Column('evidence_id', sa.UUID(), nullable=True),
+        sa.Column('show_on_profile', sa.Boolean(), server_default=sa.text('false'), nullable=False),
+        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
+        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+        sa.CheckConstraint("kind IN ('CERTIFICATE','WORK')", name='ck_portfolio_items_kind'),
+        sa.CheckConstraint('char_length(title) BETWEEN 1 AND 120', name='ck_portfolio_items_title_length'),
+        sa.CheckConstraint(
+            'issuer IS NULL OR char_length(issuer) <= 120', name='ck_portfolio_items_issuer_length'
+        ),
+        sa.CheckConstraint(
+            'credential_id IS NULL OR char_length(credential_id) <= 100',
+            name='ck_portfolio_items_credential_id_length',
+        ),
+        sa.CheckConstraint(
+            "external_url IS NULL OR (external_url LIKE 'https://%' AND char_length(external_url) <= 500)",
+            name='ck_portfolio_items_external_url_https',
+        ),
+        sa.ForeignKeyConstraint(['talent_id'], ['talent_profiles.id']),
+        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id']),
+        sa.PrimaryKeyConstraint('id'),
+        sa.UniqueConstraint('evidence_id', name='uq_portfolio_items_evidence_id'),
+    )
+    op.create_index(
+        'ix_portfolio_items_talent_not_deleted',
+        'portfolio_items',
+        ['talent_id'],
+        unique=False,
+        postgresql_where=sa.text('deleted_at IS NULL'),
+    )
+
+
+def downgrade() -> None:
+    op.drop_index('ix_portfolio_items_talent_not_deleted', table_name='portfolio_items')
+    op.drop_table('portfolio_items')
+    op.drop_constraint('ck_talent_profiles_about_length', 'talent_profiles', type_='check')
+    op.drop_column('talent_profiles', 'about')
diff --git a/backend/app/api/me.py b/backend/app/api/me.py
index 791e11b..d93f13d 100644
--- a/backend/app/api/me.py
+++ b/backend/app/api/me.py
@@ -38,6 +38,7 @@ class TalentProfileResponse(BaseModel):
     department: str | None
     study_year: int | None
     city: str | None
+    about: str | None
     visibility: str
     public_slug: str | None
     updated_at: datetime
@@ -98,9 +99,20 @@ class UpdateTalentProfileRequest(BaseModel):
     city: str | None = Field(None, max_length=100)
     department: str | None = Field(None, max_length=100)
     study_year: int | None = None
+    # Plain text "about me" (self-declared); DB CHECK mirrors the 1000-char limit.
+    about: str | None = Field(None, max_length=1000)
     visibility: str | None = None
     public_slug: str | None = Field(None, max_length=100)
 
+    @field_validator("about")
+    @classmethod
+    def normalize_about(cls, v):
+        """Whitespace-only about clears the field instead of storing blanks."""
+        if v is None:
+            return v
+        v = v.strip()
+        return v or None
+
     @field_validator("full_name")
     @classmethod
     def validate_full_name(cls, v):
@@ -201,10 +213,10 @@ def patch_talents_me(
     AC-3 through AC-7: Update current user's talent profile.
 
     Accepts:
-        - full_name, headline, city, department, study_year, visibility, public_slug
+        - full_name, headline, city, department, study_year, about, visibility, public_slug
         - Ignores: institution_id, user_id, id, talent_profile_id (if sent)
         - Explicit null on a clearable field (headline/city/department/study_year/
-          public_slug) clears it; full_name/visibility cannot be cleared (NOT NULL)
+          about/public_slug) clears it; full_name/visibility cannot be cleared (NOT NULL)
 
     Returns:
         200 + updated TalentProfile
@@ -231,7 +243,7 @@ def patch_talents_me(
     required_fields = {"full_name", "visibility"}
     set_fields = payload.model_fields_set
     updates = {}
-    for field in ["full_name", "headline", "city", "department", "study_year", "visibility", "public_slug"]:
+    for field in ["full_name", "headline", "city", "department", "study_year", "about", "visibility", "public_slug"]:
         if field not in set_fields:
             continue
         value = getattr(payload, field)
diff --git a/backend/app/api/portfolio_items.py b/backend/app/api/portfolio_items.py
new file mode 100644
index 0000000..2582cce
--- /dev/null
+++ b/backend/app/api/portfolio_items.py
@@ -0,0 +1,225 @@
+"""Portfolio item endpoints (/talents/me/portfolio-items) — the owner's certificate/work showcase.
+
+docs/arastirma-ogrenci-profili.md §4.3. Ownership always comes from the session;
+another talent's item, an unknown id and a talent-less caller answer an identical 404.
+"""
+
+import uuid
+from datetime import date, datetime, timezone
+from typing import Literal
+
+from fastapi import APIRouter, Depends, Response
+from pydantic import BaseModel, Field, field_validator
+from sqlalchemy.orm import Session
+
+from app.api.deps import get_current_principal, get_session, get_verified_principal
+from app.core.deps import require_csrf
+from app.core.errors import ApiError
+from app.services.authorization import Principal
+from app.services.portfolio import (
+    PortfolioEvidenceAlreadyLinkedError,
+    PortfolioEvidenceNotFoundError,
+    PortfolioLimitReachedError,
+    create_own_portfolio_item,
+    delete_own_portfolio_item,
+    https_host,
+    list_own_portfolio,
+    update_own_portfolio_item,
+)
+
+router = APIRouter(prefix="/talents/me/portfolio-items", tags=["portfolio-items"])
+
+
+# ============================================================================
+# Pydantic Schemas (Request/Response DTOs)
+# ============================================================================
+
+
+def _clean_optional_text(value: str | None) -> str | None:
+    if value is None:
+        return None
+    value = value.strip()
+    return value or None
+
+
+class _PortfolioFields(BaseModel):
+    """Shared validation; the DB CHECK constraints mirror every rule here."""
+
+    @field_validator("title", check_fields=False)
+    @classmethod
+    def validate_title(cls, v):
+        if v is None:
+            return v
+        v = v.strip()
+        if not v:
+            raise ValueError("title boş olamaz")
+        return v
+
+    @field_validator("issuer", "credential_id", check_fields=False)
+    @classmethod
+    def strip_text(cls, v):
+        return _clean_optional_text(v)
+
+    @field_validator("external_url", check_fields=False)
+    @classmethod
+    def validate_external_url(cls, v):
+        v = _clean_optional_text(v)
+        if v is not None and https_host(v) is None:
+            raise ValueError("external_url yalnız https:// ile başlayan geçerli bir adres olabilir")
+        return v
+
+    @field_validator("issued_on", check_fields=False)
+    @classmethod
+    def validate_issued_on(cls, v):
+        if v is not None and v > datetime.now(timezone.utc).date():
+            raise ValueError("issued_on gelecekte olamaz")
+        return v
+
+
+class CreatePortfolioItemRequest(_PortfolioFields):
+    kind: Literal["CERTIFICATE", "WORK"]
+    title: str = Field(..., max_length=120)
+    issuer: str | None = Field(None, max_length=120)
+    issued_on: date | None = None
+    credential_id: str | None = Field(None, max_length=100)
+    external_url: str | None = Field(None, max_length=500)
+    evidence_id: uuid.UUID | None = None
+    show_on_profile: bool = False
+
+
+class UpdatePortfolioItemRequest(_PortfolioFields):
+    kind: Literal["CERTIFICATE", "WORK"] | None = None
+    title: str | None = Field(None, max_length=120)
+    issuer: str | None = Field(None, max_length=120)
+    issued_on: date | None = None
+    credential_id: str | None = Field(None, max_length=100)
+    external_url: str | None = Field(None, max_length=500)
+    show_on_profile: bool | None = None
+
+
+class PortfolioItemResponse(BaseModel):
+    id: uuid.UUID
+    kind: str
+    title: str
+    issuer: str | None
+    issued_on: date | None
+    credential_id: str | None
+    external_url: str | None
+    evidence_id: uuid.UUID | None
+    show_on_profile: bool
+    # Derived on the server: COORDINATOR_CONFIRMED | COORDINATOR_REJECTED | SELF_DECLARED
+    badge: str
+    provider: str | None
+    created_at: datetime
+
+
+class EngagementCertificateResponse(BaseModel):
+    """A certificate uploaded inside an engagement, candidate for the showcase."""
+
+    evidence_id: uuid.UUID
+    created_at: datetime
+    provider: str | None
+    credential_id: str | None
+    # None: no check requested yet; otherwise PENDING | CONFIRMED | REJECTED
+    decision: str | None
+    portfolio_item_id: uuid.UUID | None
+
+
+class PortfolioListResponse(BaseModel):
+    items: list[PortfolioItemResponse]
+    engagement_certificates: list[EngagementCertificateResponse]
+
+
+# Fields that may be cleared with an explicit null; the others are NOT NULL.
+_REQUIRED_ON_UPDATE = {"kind", "title", "show_on_profile"}
+
+
+def _not_found() -> ApiError:
+    return ApiError(status_code=404, code="PORTFOLIO_ITEM_NOT_FOUND", message="Kayıt bulunamadı")
+
+
+# ============================================================================
+# Routes
+# ============================================================================
+
+
+@router.get("", response_model=PortfolioListResponse)
+def get_portfolio_items(
+    principal: Principal = Depends(get_current_principal),
+    session: Session = Depends(get_session),
+) -> PortfolioListResponse:
+    """The caller's own items (any consent state) and engagement certificates. Talent-less → empty."""
+    return PortfolioListResponse(**list_own_portfolio(session, principal))
+
+
+@router.post("", response_model=PortfolioItemResponse, status_code=201)
+def post_portfolio_item(
+    payload: CreatePortfolioItemRequest,
+    principal: Principal = Depends(get_verified_principal),
+    session: Session = Depends(get_session),
+    _csrf: None = Depends(require_csrf),
+) -> PortfolioItemResponse:
+    """
+    Errors:
+        404 EVIDENCE_NOT_FOUND: evidence_id is not the caller's own live evidence (or no talent profile)
+        409 EVIDENCE_ALREADY_IN_PORTFOLIO: that evidence already backs another item
+        409 PORTFOLIO_LIMIT_REACHED: already 50 live items
+        422: validation (title, https-only external_url, future issued_on)
+    """
+    try:
+        item = create_own_portfolio_item(session, principal, payload.model_dump())
+    except PortfolioEvidenceNotFoundError:
+        raise ApiError(status_code=404, code="EVIDENCE_NOT_FOUND", message="Kanıt bulunamadı.")
+    except PortfolioEvidenceAlreadyLinkedError:
+        raise ApiError(
+            status_code=409,
+            code="EVIDENCE_ALREADY_IN_PORTFOLIO",
+            message="Bu kanıt zaten vitrininizde.",
+        )
+    except PortfolioLimitReachedError:
+        raise ApiError(
+            status_code=409,
+            code="PORTFOLIO_LIMIT_REACHED",
+            message="En fazla 50 kayıt ekleyebilirsiniz.",
+        )
+    session.commit()
+    return PortfolioItemResponse(**item)
+
+
+@router.patch("/{item_id}", response_model=PortfolioItemResponse)
+def patch_portfolio_item(
+    item_id: uuid.UUID,
+    payload: UpdatePortfolioItemRequest,
+    principal: Principal = Depends(get_verified_principal),
+    session: Session = Depends(get_session),
+    _csrf: None = Depends(require_csrf),
+) -> PortfolioItemResponse:
+    """Update fields / "Profilde göster" consent. evidence_id cannot be changed."""
+    updates = {}
+    for field_name in payload.model_fields_set:
+        value = getattr(payload, field_name)
+        if value is None and field_name in _REQUIRED_ON_UPDATE:
+            raise ApiError(
+                status_code=422, code="FIELD_REQUIRED", message=f"{field_name} alanı boş bırakılamaz."
+            )
+        updates[field_name] = value
+
+    item = update_own_portfolio_item(session, principal, item_id, updates)
+    if item is None:
+        raise _not_found()
+    session.commit()
+    return PortfolioItemResponse(**item)
+
+
+@router.delete("/{item_id}", status_code=204)
+def delete_portfolio_item(
+    item_id: uuid.UUID,
+    principal: Principal = Depends(get_verified_principal),
+    session: Session = Depends(get_session),
+    _csrf: None = Depends(require_csrf),
+) -> Response:
+    """Soft delete; the linked evidence file stays (PRIVATE) and is not affected."""
+    if not delete_own_portfolio_item(session, principal, item_id):
+        raise _not_found()
+    session.commit()
+    return Response(status_code=204)
diff --git a/backend/app/api/public.py b/backend/app/api/public.py
index b953dc5..fdc4da3 100644
--- a/backend/app/api/public.py
+++ b/backend/app/api/public.py
@@ -102,6 +102,24 @@ class PublicSkillResponse(BaseModel):
     experience_count: int
 
 
+class PublicCertificateResponse(BaseModel):
+    """A consented portfolio item. No file, no OCR output (extracted_name/qr_raw_data/page_name)."""
+
+    kind: str
+    title: str
+    issuer: str | None
+    issued_on: date | None
+    credential_id: str | None
+    # COORDINATOR_CONFIRMED (certificate_checks decision) | SELF_DECLARED — never mixed on the page
+    badge: str
+    provider: str | None
+    # Confirmed only, https on the provider's own domain
+    verify_url: str | None
+    # Self-declared only: student's https link, shown with its host
+    link_url: str | None
+    link_host: str | None
+
+
 class PublicTalentProfileResponse(BaseModel):
     """Response schema for GET /public/talents/{slug}. No e-mail, no internal ids."""
 
@@ -112,9 +130,11 @@ class PublicTalentProfileResponse(BaseModel):
     city: str | None
     institution_name: str | None
     institution_trust_level: str | None
+    about: str | None
     verified_experiences: list[PublicVerifiedExperienceResponse]
     skills: list[PublicSkillResponse]
     attesting_organization_count: int
+    certificates: list[PublicCertificateResponse]
 
     class Config:
         from_attributes = True
@@ -140,8 +160,8 @@ def get_public_profile(
 
     Returns (200):
       - {display_name, headline, department, study_year, city, institution_name,
-         institution_trust_level, verified_experiences[], skills[],
-         attesting_organization_count} (no internal talent_id: YET-230, no e-mail)
+         institution_trust_level, about, verified_experiences[], skills[],
+         attesting_organization_count, certificates[]} (no internal talent_id: YET-230, no e-mail)
       - verified_experiences filtered to visibility='PUBLIC' only; skills derived
         from those experiences' attestations only
 
diff --git a/backend/app/main.py b/backend/app/main.py
index 742384e..6813f59 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -12,6 +12,7 @@ from app.api.institution_link_requests import router as institution_link_request
 from app.api.institutions import router as institutions_router
 from app.api.me import router as me_router
 from app.api.organizations import router as organizations_router
+from app.api.portfolio_items import router as portfolio_items_router
 from app.api.public import router as public_router
 from app.api.skills import router as skills_router
 from app.api.skill_signals import router as skill_signals_router, signals_alias_router
@@ -65,6 +66,7 @@ def create_app(environment: str) -> FastAPI:
     application.include_router(institutions_router)
     application.include_router(me_router)
     application.include_router(organizations_router)
+    application.include_router(portfolio_items_router)
     application.include_router(public_router)
     application.include_router(skills_router)
     application.include_router(skill_signals_router)
diff --git a/backend/app/models/__init__.py b/backend/app/models/__init__.py
index 36854ec..efc8c9b 100644
--- a/backend/app/models/__init__.py
+++ b/backend/app/models/__init__.py
@@ -19,6 +19,7 @@ from app.models.identity import (
 )
 from app.models.institution_link_request import InstitutionLinkRequest
 from app.models.outbox import Outbox
+from app.models.portfolio_item import PortfolioItem
 from app.models.skill import Skill
 from app.models.skill_claim import SkillClaim
 from app.models.skill_signal import SkillSignal
@@ -53,4 +54,5 @@ __all__ = [
     "Evidence",
     "FraudFlag",
     "CertificateCheck",
+    "PortfolioItem",
 ]
diff --git a/backend/app/models/identity.py b/backend/app/models/identity.py
index cc32478..551374c 100644
--- a/backend/app/models/identity.py
+++ b/backend/app/models/identity.py
@@ -10,6 +10,7 @@ from sqlalchemy import (
     Integer,
     SmallInteger,
     String,
+    Text,
     UniqueConstraint,
     text,
 )
@@ -80,6 +81,9 @@ class TalentProfile(Base, TimestampMixin):
     __tablename__ = "talent_profiles"
     __table_args__ = (
         CheckConstraint("study_year BETWEEN 1 AND 8", name="ck_talent_profiles_study_year"),
+        CheckConstraint(
+            "about IS NULL OR char_length(about) <= 1000", name="ck_talent_profiles_about_length"
+        ),
         CheckConstraint(
             "visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC')",
             name="ck_talent_profiles_visibility",
@@ -103,6 +107,8 @@ class TalentProfile(Base, TimestampMixin):
     department: Mapped[str | None] = mapped_column(String)
     study_year: Mapped[int | None] = mapped_column(SmallInteger)
     city: Mapped[str | None] = mapped_column(String)
+    # Self-written "about me" text: a claim, never shown as verified (plain text, no markup).
+    about: Mapped[str | None] = mapped_column(Text)
     visibility: Mapped[str] = mapped_column(String, nullable=False, server_default="INSTITUTION")
     public_slug: Mapped[str | None] = mapped_column(CITEXT, unique=True)
     deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
diff --git a/backend/app/models/portfolio_item.py b/backend/app/models/portfolio_item.py
new file mode 100644
index 0000000..6d59bab
--- /dev/null
+++ b/backend/app/models/portfolio_item.py
@@ -0,0 +1,74 @@
+"""
+PortfolioItem model: a talent's self-declared certificate or work shown on the profile.
+
+docs/arastirma-ogrenci-profili.md §4.2. A portfolio item is a CLAIM (final analiz
+§7.1), not evidence and not an attestation: title/issuer/date are typed by the
+student. An optional evidence_id links the uploaded file, which stays PRIVATE —
+the evidence row's own visibility CHECK is untouched, the file never goes public.
+
+The public badge is never stored here: it is derived on read. Only when the
+linked evidence has a certificate_checks row with decision=CONFIRMED (a
+coordinator's decision) is the item shown as "coordinator confirmed"; everything
+else is "self declared".
+
+Schema:
+  - id: UUIDv7 PK
+  - talent_id: FK talent_profiles.id, NOT NULL (owner, taken from the session)
+  - kind: CERTIFICATE / WORK
+  - title (1-120), issuer (<=120), issued_on, credential_id (<=100)
+  - external_url: https only (<=500)
+  - evidence_id: FK evidence.id, nullable, UNIQUE (one showcase row per file)
+  - show_on_profile: explicit consent to list it on /p/[slug], default false
+  - deleted_at: soft delete (the linked evidence is not affected)
+  - created_at, updated_at: TimestampMixin
+"""
+
+import uuid
+from datetime import date, datetime
+
+from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, UniqueConstraint, text
+from sqlalchemy.dialects.postgresql import UUID
+from sqlalchemy.orm import Mapped, mapped_column
+
+from app.models.base import Base, TimestampMixin, uuid7_default
+
+
+class PortfolioItem(Base, TimestampMixin):
+    """Self-declared certificate/work; consent-gated on the public profile."""
+
+    __tablename__ = "portfolio_items"
+    __table_args__ = (
+        UniqueConstraint("evidence_id", name="uq_portfolio_items_evidence_id"),
+        CheckConstraint("kind IN ('CERTIFICATE','WORK')", name="ck_portfolio_items_kind"),
+        CheckConstraint("char_length(title) BETWEEN 1 AND 120", name="ck_portfolio_items_title_length"),
+        CheckConstraint(
+            "issuer IS NULL OR char_length(issuer) <= 120", name="ck_portfolio_items_issuer_length"
+        ),
+        CheckConstraint(
+            "credential_id IS NULL OR char_length(credential_id) <= 100",
+            name="ck_portfolio_items_credential_id_length",
+        ),
+        CheckConstraint(
+            "external_url IS NULL OR (external_url LIKE 'https://%' AND char_length(external_url) <= 500)",
+            name="ck_portfolio_items_external_url_https",
+        ),
+        Index(
+            "ix_portfolio_items_talent_not_deleted",
+            "talent_id",
+            postgresql_where=text("deleted_at IS NULL"),
+        ),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    talent_id: Mapped[uuid.UUID] = mapped_column(
+        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
+    )
+    kind: Mapped[str] = mapped_column(String(20), nullable=False)
+    title: Mapped[str] = mapped_column(String(120), nullable=False)
+    issuer: Mapped[str | None] = mapped_column(String(120))
+    issued_on: Mapped[date | None] = mapped_column(Date)
+    credential_id: Mapped[str | None] = mapped_column(String(100))
+    external_url: Mapped[str | None] = mapped_column(String(500))
+    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id"))
+    show_on_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
+    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
diff --git a/backend/app/services/authorization.py b/backend/app/services/authorization.py
index 7f3af20..11038f7 100644
--- a/backend/app/services/authorization.py
+++ b/backend/app/services/authorization.py
@@ -10,7 +10,7 @@ from dataclasses import dataclass, field
 from sqlalchemy import Select, and_, func, or_, select
 from sqlalchemy.orm import Session
 
-from app.models import Attestation, Deliverable, Engagement, EngagementTask, Evidence, Institution, InstitutionLinkRequest, Organization, SkillClaim, SkillSignal, TalentProfile, User, VerifiedExperience
+from app.models import Attestation, CertificateCheck, Deliverable, Engagement, EngagementTask, Evidence, Institution, InstitutionLinkRequest, Organization, PortfolioItem, SkillClaim, SkillSignal, TalentProfile, User, VerifiedExperience
 
 
 @dataclass
@@ -388,6 +388,52 @@ def scoped_own_institution_link_requests(session: Session, principal: Principal)
     return select(InstitutionLinkRequest).where(InstitutionLinkRequest.id.in_([]))
 
 
+def scoped_own_portfolio_items(session: Session, principal: Principal) -> Select:
+    """
+    The principal's own, not soft-deleted portfolio items (docs/arastirma-ogrenci-profili.md §4.3).
+
+    Ownership comes from principal.talent_id (the session), never from the URL or body.
+    Another talent's item, an unknown id and a talent-less principal are all out of
+    scope, so callers answer an identical 404.
+    """
+    if principal.talent_id is not None:
+        return select(PortfolioItem).where(
+            PortfolioItem.talent_id == principal.talent_id,
+            PortfolioItem.deleted_at.is_(None),
+        )
+    return select(PortfolioItem).where(PortfolioItem.id.in_([]))
+
+
+def scoped_public_portfolio_items(session: Session, talent_id: uuid.UUID) -> Select:
+    """
+    (PortfolioItem, CertificateCheck | None) rows the owner consented to show publicly.
+
+    Used only by the public profile, after the talent was resolved via
+    scoped_public_talent_profile() — talent visibility is not re-checked here.
+    Kept: show_on_profile AND not deleted. The certificate check is joined only
+    through evidence that is the same talent's and not deleted, so a badge can
+    never be borrowed from someone else's file. Callers must not expose the
+    check's extracted_name/qr_raw_data/page_name or the evidence file.
+    """
+    return (
+        select(PortfolioItem, CertificateCheck)
+        .outerjoin(
+            Evidence,
+            and_(
+                Evidence.id == PortfolioItem.evidence_id,
+                Evidence.owner_talent_id == PortfolioItem.talent_id,
+                Evidence.deleted_at.is_(None),
+            ),
+        )
+        .outerjoin(CertificateCheck, CertificateCheck.evidence_id == Evidence.id)
+        .where(
+            PortfolioItem.talent_id == talent_id,
+            PortfolioItem.show_on_profile.is_(True),
+            PortfolioItem.deleted_at.is_(None),
+        )
+    )
+
+
 def get_scoped_or_404(scoped_select: Select, session: Session):
     """
     Execute a scoped query and return first result or None.
diff --git a/backend/app/services/portfolio.py b/backend/app/services/portfolio.py
new file mode 100644
index 0000000..c6cba36
--- /dev/null
+++ b/backend/app/services/portfolio.py
@@ -0,0 +1,330 @@
+"""
+Portfolio items: the talent's own certificates/works on the profile
+(docs/arastirma-ogrenci-profili.md §4).
+
+A portfolio item is a self-declared claim. Its public badge is derived here and
+never chosen by the student:
+  - COORDINATOR_CONFIRMED: the linked evidence (same owner, not deleted) has a
+    certificate_checks row with decision=CONFIRMED — a coordinator's decision.
+  - COORDINATOR_REJECTED (owner only): the coordinator rejected it; such an item
+    is never listed publicly, not even as a self-declared claim.
+  - SELF_DECLARED: everything else.
+The evidence file always stays PRIVATE; only summary fields reach the public page.
+"""
+
+import uuid
+from dataclasses import dataclass
+from datetime import date, datetime, timezone
+from urllib.parse import urlsplit
+
+from sqlalchemy import func, select
+from sqlalchemy.exc import IntegrityError
+from sqlalchemy.orm import Session
+
+from app.models import CertificateCheck, Evidence, PortfolioItem
+from app.services.audit import log_audit_event
+from app.services.authorization import (
+    Principal,
+    get_scoped_or_404,
+    scoped_evidence,
+    scoped_own_portfolio_items,
+    scoped_public_portfolio_items,
+)
+from app.services.certificate_check import get_certificate_check_for_evidence
+
+CONFIRMED = "COORDINATOR_CONFIRMED"
+REJECTED = "COORDINATOR_REJECTED"
+SELF_DECLARED = "SELF_DECLARED"
+
+# Live items per talent; bounds the public payload (atdd AC-S11).
+MAX_ITEMS_PER_TALENT = 50
+
+# Official verification pages only; anything else is never rendered as a link
+# (open redirect / phishing on a page that carries our "confirmed" badge).
+OFFICIAL_VERIFY_HOSTS = frozenset(
+    {"coursera.org", "www.coursera.org", "udemy.com", "www.udemy.com", "ude.my"}
+)
+
+EDITABLE_FIELDS = ("kind", "title", "issuer", "issued_on", "credential_id", "external_url", "show_on_profile")
+
+
+class PortfolioEvidenceNotFoundError(Exception):
+    """evidence_id is not the caller's own, live evidence (404)."""
+
+
+class PortfolioEvidenceAlreadyLinkedError(Exception):
+    """The evidence already backs another portfolio item (409)."""
+
+
+class PortfolioLimitReachedError(Exception):
+    """The talent already has MAX_ITEMS_PER_TALENT live items (409)."""
+
+
+def https_host(url: str | None) -> str | None:
+    """ASCII (punycode) host of a plain https URL (no credentials, default port), else None.
+
+    Punycode makes IDN homographs visible ("gооgle.com" → "xn--ggle-55da.com").
+    """
+    if not url:
+        return None
+    try:
+        parts = urlsplit(url)
+        port = parts.port
+    except ValueError:
+        return None
+    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
+        return None
+    if port not in (None, 443):
+        return None
+    try:
+        return parts.hostname.encode("idna").decode("ascii").lower()
+    except UnicodeError:
+        return None
+
+
+def official_verify_url(url: str | None) -> str | None:
+    """The URL itself when it is https on a provider's own domain, else None."""
+    host = https_host(url)
+    return url if host in OFFICIAL_VERIFY_HOSTS else None
+
+
+def _badge(check: CertificateCheck | None) -> str:
+    if check is not None and check.decision == "CONFIRMED":
+        return CONFIRMED
+    if check is not None and check.decision == "REJECTED":
+        return REJECTED
+    return SELF_DECLARED
+
+
+def _own_check(session: Session, principal: Principal, item: PortfolioItem) -> CertificateCheck | None:
+    """Certificate check of the item's evidence, only while that evidence is the caller's and live."""
+    if item.evidence_id is None:
+        return None
+    evidence = get_scoped_or_404(
+        scoped_evidence(session, principal).where(
+            Evidence.id == item.evidence_id, Evidence.deleted_at.is_(None)
+        ),
+        session,
+    )
+    if evidence is None:
+        return None
+    return get_certificate_check_for_evidence(session, principal, evidence.id)
+
+
+def _serialize(session: Session, principal: Principal, item: PortfolioItem) -> dict:
+    check = _own_check(session, principal, item)
+    return {
+        "id": item.id,
+        "kind": item.kind,
+        "title": item.title,
+        "issuer": item.issuer,
+        "issued_on": item.issued_on,
+        "credential_id": item.credential_id,
+        "external_url": item.external_url,
+        "evidence_id": item.evidence_id,
+        "show_on_profile": item.show_on_profile,
+        "badge": _badge(check),
+        "provider": check.provider if check is not None else None,
+        "created_at": item.created_at,
+    }
+
+
+def _get_own(session: Session, principal: Principal, item_id: uuid.UUID) -> PortfolioItem | None:
+    return get_scoped_or_404(
+        scoped_own_portfolio_items(session, principal).where(PortfolioItem.id == item_id), session
+    )
+
+
+def list_own_portfolio(session: Session, principal: Principal) -> dict:
+    """The caller's items plus engagement certificates that could be added to the showcase."""
+    items = (
+        session.execute(
+            scoped_own_portfolio_items(session, principal).order_by(PortfolioItem.created_at.desc())
+        )
+        .scalars()
+        .all()
+    )
+    linked = {item.evidence_id: item.id for item in items if item.evidence_id is not None}
+
+    certificates = (
+        session.execute(
+            scoped_evidence(session, principal)
+            .where(
+                Evidence.kind == "CERTIFICATE",
+                Evidence.deliverable_id.isnot(None),
+                Evidence.deleted_at.is_(None),
+            )
+            .order_by(Evidence.created_at.desc())
+        )
+        .scalars()
+        .all()
+    )
+    engagement_certificates = []
+    for evidence in certificates:
+        check = get_certificate_check_for_evidence(session, principal, evidence.id)
+        engagement_certificates.append(
+            {
+                "evidence_id": evidence.id,
+                "created_at": evidence.created_at,
+                "provider": check.provider if check is not None else None,
+                "credential_id": check.credential_id if check is not None else None,
+                "decision": check.decision if check is not None else None,
+                "portfolio_item_id": linked.get(evidence.id),
+            }
+        )
+
+    return {
+        "items": [_serialize(session, principal, item) for item in items],
+        "engagement_certificates": engagement_certificates,
+    }
+
+
+def create_own_portfolio_item(session: Session, principal: Principal, data: dict) -> dict:
+    """New item owned by the caller. A linked evidence must be the caller's own, live evidence."""
+    if principal.talent_id is None:
+        raise PortfolioEvidenceNotFoundError("talent-less principal")
+    evidence_id = data.get("evidence_id")
+    if evidence_id is not None:
+        evidence = get_scoped_or_404(
+            scoped_evidence(session, principal).where(
+                Evidence.id == evidence_id, Evidence.deleted_at.is_(None)
+            ),
+            session,
+        )
+        if evidence is None:
+            raise PortfolioEvidenceNotFoundError(str(evidence_id))
+
+    live_count = session.execute(
+        select(func.count()).select_from(scoped_own_portfolio_items(session, principal).subquery())
+    ).scalar_one()
+    if live_count >= MAX_ITEMS_PER_TALENT:
+        raise PortfolioLimitReachedError(str(principal.talent_id))
+
+    item = PortfolioItem(talent_id=principal.talent_id, **{k: v for k, v in data.items() if v is not None})
+    session.add(item)
+    try:
+        with session.begin_nested():
+            session.flush()
+    except IntegrityError as exc:
+        if "uq_portfolio_items_evidence_id" not in str(exc.orig):
+            raise
+        raise PortfolioEvidenceAlreadyLinkedError(str(evidence_id)) from exc
+
+    log_audit_event(
+        session,
+        actor_user_id=principal.user_id,
+        actor_ip=None,
+        action="PORTFOLIO_ITEM_CREATED",
+        subject_type="portfolio_item",
+        subject_id=item.id,
+        result="SUCCESS",
+        metadata={"kind": item.kind, "show_on_profile": item.show_on_profile},
+    )
+    session.refresh(item)
+    return _serialize(session, principal, item)
+
+
+def update_own_portfolio_item(
+    session: Session, principal: Principal, item_id: uuid.UUID, updates: dict
+) -> dict | None:
+    """Apply the provided fields; None when the item is not the caller's (→ 404)."""
+    item = _get_own(session, principal, item_id)
+    if item is None:
+        return None
+
+    previous_consent = item.show_on_profile
+    for field_name, value in updates.items():
+        if field_name in EDITABLE_FIELDS:
+            setattr(item, field_name, value)
+    item.updated_at = datetime.now(timezone.utc)
+    session.flush()
+
+    if item.show_on_profile != previous_consent:
+        log_audit_event(
+            session,
+            actor_user_id=principal.user_id,
+            actor_ip=None,
+            action="PORTFOLIO_ITEM_VISIBILITY_CHANGED",
+            subject_type="portfolio_item",
+            subject_id=item.id,
+            result="SUCCESS",
+            metadata={"from": previous_consent, "to": item.show_on_profile},
+        )
+    return _serialize(session, principal, item)
+
+
+def delete_own_portfolio_item(session: Session, principal: Principal, item_id: uuid.UUID) -> bool:
+    """Soft delete; the linked evidence file is not touched. False when not the caller's (→ 404)."""
+    item = _get_own(session, principal, item_id)
+    if item is None:
+        return False
+    item.deleted_at = datetime.now(timezone.utc)
+    item.show_on_profile = False
+    session.flush()
+    log_audit_event(
+        session,
+        actor_user_id=principal.user_id,
+        actor_ip=None,
+        action="PORTFOLIO_ITEM_DELETED",
+        subject_type="portfolio_item",
+        subject_id=item.id,
+        result="SUCCESS",
+        metadata=None,
+    )
+    return True
+
+
+@dataclass
+class PublicCertificate:
+    kind: str
+    title: str
+    issuer: str | None
+    issued_on: date | None
+    credential_id: str | None
+    badge: str
+    provider: str | None
+    # COORDINATOR_CONFIRMED only, and only on an allowlisted provider domain.
+    verify_url: str | None
+    # SELF_DECLARED only: the student's own https link, rendered with its host visible.
+    link_url: str | None
+    link_host: str | None
+
+
+def build_public_certificates(session: Session, talent_id: uuid.UUID) -> list[PublicCertificate]:
+    """Consented items of an already-resolved PUBLIC talent; confirmed first, then newest.
+
+    On a confirmed card provider and credential number come only from the
+    coordinator-reviewed check, never from what the student typed (atdd AC-S6).
+    """
+    result: list[tuple[PublicCertificate, datetime]] = []
+    for item, check in session.execute(scoped_public_portfolio_items(session, talent_id)).all():
+        badge = _badge(check)
+        if badge == REJECTED:
+            continue
+        confirmed = badge == CONFIRMED
+        link_host = None if confirmed else https_host(item.external_url)
+        result.append(
+            (
+                PublicCertificate(
+                    kind=item.kind,
+                    title=item.title,
+                    issuer=None if confirmed else item.issuer,
+                    issued_on=item.issued_on,
+                    credential_id=check.credential_id if confirmed else item.credential_id,
+                    badge=badge,
+                    provider=check.provider if confirmed else None,
+                    verify_url=official_verify_url(check.verify_url) if confirmed else None,
+                    link_url=item.external_url if link_host else None,
+                    link_host=link_host,
+                ),
+                item.created_at,
+            )
+        )
+    result.sort(
+        key=lambda pair: (
+            pair[0].badge != CONFIRMED,
+            -(pair[0].issued_on or date.min).toordinal(),
+            -pair[1].timestamp(),
+        )
+    )
+    return [cert for cert, _ in result[:MAX_ITEMS_PER_TALENT]]
diff --git a/backend/app/services/public_profile.py b/backend/app/services/public_profile.py
index 63c1d32..65b431a 100644
--- a/backend/app/services/public_profile.py
+++ b/backend/app/services/public_profile.py
@@ -24,6 +24,7 @@ from app.services.authorization import (
     scoped_public_skill_signals,
     scoped_public_verified_experiences,
 )
+from app.services.portfolio import PublicCertificate, build_public_certificates
 from app.services.visibility_service import filter_public_experiences
 
 # Higher index = stronger evidence. Mirrors skill_signals.strength CHECK.
@@ -78,9 +79,13 @@ class PublicProfile:
     city: str | None
     institution_name: str | None
     institution_trust_level: str | None
+    # Self-declared text; the page labels it "Kendi beyanı", never as verified.
+    about: str | None
     verified_experiences: list[PublicExperience]
     skills: list[PublicSkill]
     attesting_organization_count: int
+    # Consented portfolio items only (show_on_profile); file and OCR fields never included.
+    certificates: list[PublicCertificate] = field(default_factory=list)
 
 
 @dataclass
@@ -197,7 +202,9 @@ def build_public_profile(session: Session, talent: TalentProfile) -> PublicProfi
         city=talent.city,
         institution_name=institution.name if institution else None,
         institution_trust_level=institution.verification_level if institution else None,
+        about=talent.about,
         verified_experiences=public_experiences,
         skills=skills,
         attesting_organization_count=len(attestor_orgs),
+        certificates=build_public_certificates(session, talent.id),
     )
diff --git a/backend/tests/authorization/test_portfolio_items_authz.py b/backend/tests/authorization/test_portfolio_items_authz.py
new file mode 100644
index 0000000..d5488b4
--- /dev/null
+++ b/backend/tests/authorization/test_portfolio_items_authz.py
@@ -0,0 +1,415 @@
+"""
+Authorization tests for /talents/me/portfolio-items and the public certificates list.
+
+docs/arastirma-ogrenci-profili.md §4.3-4.4:
+- Owner only; ownership from the session. Another talent's item, an unknown id and
+  a talent-less caller answer an identical 404 and leave the record untouched.
+- evidence_id must be the caller's own live evidence (someone else's → 404).
+- Public profile lists only consented (show_on_profile) items of a PUBLIC talent;
+  file and OCR fields never leak; the "coordinator confirmed" badge can only come
+  from a CONFIRMED check on the owner's own evidence.
+"""
+
+import uuid
+from datetime import datetime, timezone
+
+import pytest
+from sqlalchemy import select
+
+from app.models import (
+    AuditEvent,
+    CertificateCheck,
+    Deliverable,
+    Engagement,
+    Evidence,
+    Organization,
+    PortfolioItem,
+    User,
+)
+
+BASE = "/talents/me/portfolio-items"
+
+
+def _auth(user) -> dict:
+    return {"X-Debug-User-Id": str(user.id)}
+
+
+def _item(session, talent, **kwargs) -> PortfolioItem:
+    fields = {"kind": "CERTIFICATE", "title": "Veri Analizi Sertifikası", "show_on_profile": False}
+    fields.update(kwargs)
+    item = PortfolioItem(talent_id=talent.id, **fields)
+    session.add(item)
+    session.flush()
+    return item
+
+
+def _evidence(session, talent, deliverable_id=None) -> Evidence:
+    ev = Evidence(
+        owner_talent_id=talent.id,
+        kind="CERTIFICATE",
+        storage_key=f"evidence/{talent.id}/{uuid.uuid4()}.png",
+        mime_type="image/png",
+        size_bytes=100,
+        scan_status="CLEAN",
+        deliverable_id=deliverable_id,
+    )
+    session.add(ev)
+    session.flush()
+    return ev
+
+
+@pytest.fixture
+def item_a(session, talent_a):
+    return _item(session, talent_a, title="A sertifikası")
+
+
+@pytest.fixture
+def item_b(session, talent_b):
+    return _item(session, talent_b, title="B sertifikası")
+
+
+@pytest.fixture
+def talentless_user(session):
+    user = User(email="portfolio-org-member@example.com", password_hash="hash")
+    session.add(user)
+    session.flush()
+    return user
+
+
+# ---------------------------------------------------------------------------
+# Owner — positive
+# ---------------------------------------------------------------------------
+
+
+def test_owner_creates_lists_updates_and_deletes(client, session, user_talent_a, talent_a):
+    created = client.post(
+        BASE,
+        json={"kind": "WORK", "title": "Kişisel web sitesi", "external_url": "https://ornek.dev"},
+        headers=_auth(user_talent_a),
+    )
+    assert created.status_code == 201, created.text
+    body = created.json()
+    assert body["badge"] == "SELF_DECLARED"
+    assert body["show_on_profile"] is False  # consent defaults to off
+    item_id = body["id"]
+
+    listed = client.get(BASE, headers=_auth(user_talent_a))
+    assert listed.status_code == 200
+    assert [i["id"] for i in listed.json()["items"]] == [item_id]
+
+    patched = client.patch(f"{BASE}/{item_id}", json={"show_on_profile": True}, headers=_auth(user_talent_a))
+    assert patched.status_code == 200
+    assert patched.json()["show_on_profile"] is True
+
+    deleted = client.delete(f"{BASE}/{item_id}", headers=_auth(user_talent_a))
+    assert deleted.status_code == 204
+    assert client.get(BASE, headers=_auth(user_talent_a)).json()["items"] == []
+    row = session.get(PortfolioItem, uuid.UUID(item_id))
+    assert row.deleted_at is not None and row.show_on_profile is False
+
+
+def test_owner_can_link_own_evidence(client, session, user_talent_a, talent_a):
+    ev = _evidence(session, talent_a)
+    response = client.post(
+        BASE,
+        json={"kind": "CERTIFICATE", "title": "Dosyalı sertifika", "evidence_id": str(ev.id)},
+        headers=_auth(user_talent_a),
+    )
+    assert response.status_code == 201, response.text
+    assert response.json()["evidence_id"] == str(ev.id)
+
+    again = client.post(
+        BASE,
+        json={"kind": "CERTIFICATE", "title": "İkinci kez", "evidence_id": str(ev.id)},
+        headers=_auth(user_talent_a),
+    )
+    assert again.status_code == 409
+    assert again.json()["code"] == "EVIDENCE_ALREADY_IN_PORTFOLIO"
+
+
+def test_consent_change_is_audited(client, session, user_talent_a, talent_a, item_a):
+    client.patch(f"{BASE}/{item_a.id}", json={"show_on_profile": True}, headers=_auth(user_talent_a))
+
+    events = session.execute(
+        select(AuditEvent).where(
+            AuditEvent.action == "PORTFOLIO_ITEM_VISIBILITY_CHANGED",
+            AuditEvent.subject_id == item_a.id,
+        )
+    ).scalars().all()
+    assert len(events) == 1
+    assert events[0].actor_user_id == user_talent_a.id
+    assert events[0].event_metadata == {"from": False, "to": True}
+
+
+# ---------------------------------------------------------------------------
+# Negative — identical 404, record untouched
+# ---------------------------------------------------------------------------
+
+
+def test_other_talent_cannot_update_or_delete(client, session, user_talent_a, talent_a, item_b):
+    patched = client.patch(f"{BASE}/{item_b.id}", json={"show_on_profile": True}, headers=_auth(user_talent_a))
+    deleted = client.delete(f"{BASE}/{item_b.id}", headers=_auth(user_talent_a))
+
+    assert patched.status_code == deleted.status_code == 404
+    assert patched.json()["code"] == "PORTFOLIO_ITEM_NOT_FOUND"
+    session.refresh(item_b)
+    assert item_b.show_on_profile is False
+    assert item_b.deleted_at is None
+
+
+def test_other_talent_items_not_listed(client, user_talent_a, talent_a, item_a, item_b):
+    ids = [i["id"] for i in client.get(BASE, headers=_auth(user_talent_a)).json()["items"]]
+    assert ids == [str(item_a.id)]
+
+
+def test_foreign_and_unknown_ids_are_indistinguishable(client, user_talent_a, talent_a, item_b):
+    foreign = client.patch(f"{BASE}/{item_b.id}", json={"title": "x"}, headers=_auth(user_talent_a))
+    unknown = client.patch(f"{BASE}/{uuid.uuid4()}", json={"title": "x"}, headers=_auth(user_talent_a))
+
+    assert foreign.status_code == unknown.status_code == 404
+    strip = lambda r: {k: v for k, v in r.json().items() if k != "request_id"}  # noqa: E731
+    assert strip(foreign) == strip(unknown)
+
+
+def test_cannot_link_someone_elses_evidence(client, session, user_talent_a, talent_a, talent_b):
+    foreign_ev = _evidence(session, talent_b)
+    response = client.post(
+        BASE,
+        json={"kind": "CERTIFICATE", "title": "Çalıntı", "evidence_id": str(foreign_ev.id)},
+        headers=_auth(user_talent_a),
+    )
+    assert response.status_code == 404
+    assert response.json()["code"] == "EVIDENCE_NOT_FOUND"
+    assert session.execute(select(PortfolioItem).where(PortfolioItem.evidence_id == foreign_ev.id)).first() is None
+
+
+def test_cannot_link_deleted_evidence(client, session, user_talent_a, talent_a):
+    ev = _evidence(session, talent_a)
+    ev.deleted_at = datetime.now(timezone.utc)
+    session.flush()
+    response = client.post(
+        BASE, json={"kind": "CERTIFICATE", "title": "Silinmiş", "evidence_id": str(ev.id)}, headers=_auth(user_talent_a)
+    )
+    assert response.status_code == 404
+
+
+def test_talent_id_in_body_is_ignored(client, session, user_talent_a, talent_a, talent_b):
+    response = client.post(
+        BASE,
+        json={"kind": "WORK", "title": "Kimin?", "talent_id": str(talent_b.id)},
+        headers=_auth(user_talent_a),
+    )
+    assert response.status_code == 201
+    row = session.get(PortfolioItem, uuid.UUID(response.json()["id"]))
+    assert row.talent_id == talent_a.id
+
+
+def test_talentless_user(client, talentless_user, item_a):
+    assert client.get(BASE, headers=_auth(talentless_user)).json() == {"items": [], "engagement_certificates": []}
+    assert client.patch(f"{BASE}/{item_a.id}", json={"title": "x"}, headers=_auth(talentless_user)).status_code == 404
+    assert client.delete(f"{BASE}/{item_a.id}", headers=_auth(talentless_user)).status_code == 404
+    assert client.post(BASE, json={"kind": "WORK", "title": "x"}, headers=_auth(talentless_user)).status_code == 404
+
+
+def test_unauthenticated_is_rejected(client, item_a):
+    assert client.get(BASE).status_code == 401
+    assert client.post(BASE, json={"kind": "WORK", "title": "x"}).status_code == 401
+    assert client.patch(f"{BASE}/{item_a.id}", json={"title": "x"}).status_code == 401
+    assert client.delete(f"{BASE}/{item_a.id}").status_code == 401
+
+
+# ---------------------------------------------------------------------------
+# Public profile — consent, privacy, badge integrity
+# ---------------------------------------------------------------------------
+
+
+@pytest.fixture
+def public_talent_a(session, talent_a):
+    talent_a.visibility = "PUBLIC"
+    talent_a.public_slug = "portfolyo-a"
+    session.flush()
+    return talent_a
+
+
+@pytest.fixture
+def engagement_certificate_a(session, user_talent_a, public_talent_a):
+    org = Organization(name="Portfolyo Org", verification_level="T2")
+    session.add(org)
+    session.flush()
+    engagement = Engagement(
+        talent_id=public_talent_a.id,
+        organization_id=org.id,
+        institution_id=None,
+        kind="SHORT_PROJECT",
+        title="Sertifikalı çalışma",
+        status="ACTIVE",
+        version=1,
+    )
+    session.add(engagement)
+    session.flush()
+    deliverable = Deliverable(
+        engagement_id=engagement.id,
+        title="Çıktı",
+        submitted_by_user_id=user_talent_a.id,
+        submitted_at=datetime.now(timezone.utc),
+    )
+    session.add(deliverable)
+    session.flush()
+    ev = _evidence(session, public_talent_a, deliverable_id=deliverable.id)
+    check = CertificateCheck(
+        evidence_id=ev.id,
+        status="DONE",
+        provider="COURSERA",
+        credential_id="ABC123XYZ",
+        verify_url="https://www.coursera.org/verify/ABC123XYZ",
+        qr_raw_data="https://www.coursera.org/verify/ABC123XYZ",
+        extracted_name="Gizli Ad Soyad",
+        name_match=True,
+        page_name="Gizli Sayfa Adı",
+        decision="CONFIRMED",
+    )
+    session.add(check)
+    session.flush()
+    return ev
+
+
+def test_public_lists_only_consented_items(client, session, public_talent_a):
+    _item(session, public_talent_a, title="Gizli kalan", show_on_profile=False)
+    _item(session, public_talent_a, title="Görünen", show_on_profile=True)
+    _item(session, public_talent_a, title="Silinmiş", show_on_profile=True, deleted_at=datetime.now(timezone.utc))
+
+    body = client.get("/public/talents/portfolyo-a").json()
+    assert [c["title"] for c in body["certificates"]] == ["Görünen"]
+    assert body["certificates"][0]["badge"] == "SELF_DECLARED"
+
+
+def test_non_public_talent_exposes_nothing(client, session, talent_a):
+    talent_a.public_slug = "portfolyo-gizli"
+    session.flush()
+    _item(session, talent_a, title="Rızalı ama profil kapalı", show_on_profile=True)
+
+    response = client.get("/public/talents/portfolyo-gizli")
+    assert response.status_code == 404
+    assert "Rızalı" not in response.text
+
+
+def test_confirmed_certificate_exposes_summary_only(client, session, public_talent_a, engagement_certificate_a):
+    _item(session, public_talent_a, title="Coursera — Veri Bilimi", evidence_id=engagement_certificate_a.id, show_on_profile=True)
+
+    response = client.get("/public/talents/portfolyo-a")
+    cert = response.json()["certificates"][0]
+    assert cert["badge"] == "COORDINATOR_CONFIRMED"
+    assert cert["provider"] == "COURSERA"
+    assert cert["credential_id"] == "ABC123XYZ"
+    assert cert["verify_url"] == "https://www.coursera.org/verify/ABC123XYZ"
+    assert cert["link_url"] is None
+    for leaked in ("Gizli Ad Soyad", "Gizli Sayfa Adı", "storage_key", "evidence/", str(engagement_certificate_a.id)):
+        assert leaked not in response.text
+
+
+def test_badge_cannot_be_borrowed_from_foreign_evidence(client, session, public_talent_a, talent_b, engagement_certificate_a):
+    """A CONFIRMED check on talent A's evidence must not make talent B's row confirmed,
+    even if a row were (bypassing the API) pointed at that evidence."""
+    talent_b.visibility = "PUBLIC"
+    talent_b.public_slug = "portfolyo-b"
+    session.flush()
+    _item(session, talent_b, title="Ödünç rozet", evidence_id=engagement_certificate_a.id, show_on_profile=True)
+
+    cert = client.get("/public/talents/portfolyo-b").json()["certificates"][0]
+    assert cert["badge"] == "SELF_DECLARED"
+    assert cert["verify_url"] is None and cert["provider"] is None
+
+
+def _set_decision(session, evidence, decision):
+    check = session.execute(select(CertificateCheck).where(CertificateCheck.evidence_id == evidence.id)).scalar_one()
+    check.decision = decision
+    session.flush()
+
+
+def test_pending_check_is_self_declared(client, session, public_talent_a, engagement_certificate_a):
+    _set_decision(session, engagement_certificate_a, "PENDING")
+    _item(session, public_talent_a, title="Bekleyen", evidence_id=engagement_certificate_a.id, show_on_profile=True)
+
+    cert = client.get("/public/talents/portfolyo-a").json()["certificates"][0]
+    assert cert["badge"] == "SELF_DECLARED"
+    assert cert["verify_url"] is None and cert["provider"] is None
+
+
+def test_rejected_certificate_is_hidden_publicly(client, session, user_talent_a, public_talent_a, engagement_certificate_a):
+    """AC-S7: a coordinator-rejected certificate never reaches the public page, not even as a claim."""
+    _set_decision(session, engagement_certificate_a, "REJECTED")
+    item = _item(session, public_talent_a, title="Reddedilmiş", evidence_id=engagement_certificate_a.id, show_on_profile=True)
+
+    assert client.get("/public/talents/portfolyo-a").json()["certificates"] == []
+    own = client.get(BASE, headers=_auth(user_talent_a)).json()["items"]
+    assert [(i["id"], i["badge"]) for i in own] == [(str(item.id), "COORDINATOR_REJECTED")]
+
+
+def test_confirmed_card_ignores_student_typed_credential(client, session, public_talent_a, engagement_certificate_a):
+    """AC-S6: on a confirmed card credential number/provider come only from the reviewed check."""
+    _item(
+        session,
+        public_talent_a,
+        title="Onaylı",
+        issuer="Google",
+        credential_id="SAHTE-999",
+        evidence_id=engagement_certificate_a.id,
+        show_on_profile=True,
+    )
+    cert = client.get("/public/talents/portfolyo-a").json()["certificates"][0]
+    assert cert["badge"] == "COORDINATOR_CONFIRMED"
+    assert cert["credential_id"] == "ABC123XYZ"
+    assert cert["issuer"] is None
+    assert cert["provider"] == "COURSERA"
+
+
+def test_client_cannot_forge_badge_or_relink_evidence(client, session, user_talent_a, talent_a, engagement_certificate_a):
+    """AC-S4: badge/provider/decision in the body are ignored; PATCH cannot move evidence_id."""
+    created = client.post(
+        BASE,
+        json={
+            "kind": "CERTIFICATE",
+            "title": "Sahte onay",
+            "badge": "COORDINATOR_CONFIRMED",
+            "provider": "COURSERA",
+            "decision": "CONFIRMED",
+        },
+        headers=_auth(user_talent_a),
+    )
+    assert created.status_code == 201
+    assert created.json()["badge"] == "SELF_DECLARED"
+    item_id = created.json()["id"]
+
+    patched = client.patch(
+        f"{BASE}/{item_id}",
+        json={"evidence_id": str(engagement_certificate_a.id), "badge": "COORDINATOR_CONFIRMED"},
+        headers=_auth(user_talent_a),
+    )
+    assert patched.status_code == 200
+    assert patched.json()["evidence_id"] is None
+    assert patched.json()["badge"] == "SELF_DECLARED"
+
+
+def test_non_provider_verify_url_is_dropped(client, session, public_talent_a, engagement_certificate_a):
+    check = session.execute(
+        select(CertificateCheck).where(CertificateCheck.evidence_id == engagement_certificate_a.id)
+    ).scalar_one()
+    check.verify_url = "https://coursera.org.evil.example/verify/ABC"
+    session.flush()
+    _item(session, public_talent_a, title="Şüpheli link", evidence_id=engagement_certificate_a.id, show_on_profile=True)
+
+    cert = client.get("/public/talents/portfolyo-a").json()["certificates"][0]
+    assert cert["badge"] == "COORDINATOR_CONFIRMED"
+    assert cert["verify_url"] is None
+
+
+def test_public_certificate_keys_are_an_exact_allowlist(client, session, public_talent_a, engagement_certificate_a):
+    """Any new key on a public certificate must be a deliberate decision (leak guard)."""
+    _item(session, public_talent_a, title="Onaylı", evidence_id=engagement_certificate_a.id, show_on_profile=True)
+    _item(session, public_talent_a, title="Beyan", show_on_profile=True)
+
+    for cert in client.get("/public/talents/portfolyo-a").json()["certificates"]:
+        assert set(cert) == {
+            "kind", "title", "issuer", "issued_on", "credential_id",
+            "badge", "provider", "verify_url", "link_url", "link_host",
+        }
diff --git a/backend/tests/authorization/test_public_l05_internal_ids_and_deleted_talent.py b/backend/tests/authorization/test_public_l05_internal_ids_and_deleted_talent.py
index 4fff6d4..cec98be 100644
--- a/backend/tests/authorization/test_public_l05_internal_ids_and_deleted_talent.py
+++ b/backend/tests/authorization/test_public_l05_internal_ids_and_deleted_talent.py
@@ -83,6 +83,8 @@ def test_public_profile_does_not_expose_talent_or_user_id(client, profile, user,
         "display_name", "headline", "department", "study_year", "city",
         "institution_name", "institution_trust_level",
         "verified_experiences", "skills", "attesting_organization_count",
+            # docs/arastirma-ogrenci-profili.md §4.4: self-declared about + consented certificates
+            "about", "certificates",
     }
     assert str(profile.id) not in response.text
     assert str(user.id) not in response.text
diff --git a/backend/tests/authorization/test_public_profile_authz.py b/backend/tests/authorization/test_public_profile_authz.py
index 2e277fa..873ba76 100644
--- a/backend/tests/authorization/test_public_profile_authz.py
+++ b/backend/tests/authorization/test_public_profile_authz.py
@@ -455,6 +455,8 @@ class TestSecurityMatrixRow5PublicTalent:
             "display_name", "headline", "department", "study_year", "city",
             "institution_name", "institution_trust_level",
             "verified_experiences", "skills", "attesting_organization_count",
+            # docs/arastirma-ogrenci-profili.md §4.4: self-declared about + consented certificates
+            "about", "certificates",
         }
 
         assert response_keys == expected_keys, (
diff --git a/backend/tests/test_portfolio_items.py b/backend/tests/test_portfolio_items.py
new file mode 100644
index 0000000..7f21a5e
--- /dev/null
+++ b/backend/tests/test_portfolio_items.py
@@ -0,0 +1,210 @@
+"""
+Domain/validation tests for "Hakkımda" (talent_profiles.about) and portfolio items
+(docs/arastirma-ogrenci-profili.md §4). Authorization lives in
+tests/authorization/test_portfolio_items_authz.py.
+"""
+
+from datetime import date, timedelta
+
+import pytest
+from sqlalchemy.exc import IntegrityError
+
+from app.models import PortfolioItem, TalentProfile, User
+from app.services.portfolio import MAX_ITEMS_PER_TALENT, https_host, official_verify_url
+
+BASE = "/talents/me/portfolio-items"
+
+
+@pytest.fixture
+def owner(session):
+    user = User(email="portfolio-owner@example.com", password_hash="hash")
+    session.add(user)
+    session.flush()
+    profile = TalentProfile(user_id=user.id, full_name="Portfolyo Sahibi", visibility="PUBLIC", public_slug="portfolyo-sahibi")
+    session.add(profile)
+    session.flush()
+    return user, profile
+
+
+def _auth(user) -> dict:
+    return {"X-Debug-User-Id": str(user.id)}
+
+
+# ---------------------------------------------------------------------------
+# URL helpers
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.parametrize(
+    "url, host",
+    [
+        ("https://www.coursera.org/verify/X", "www.coursera.org"),
+        ("https://Credential.NET/abc", "credential.net"),
+        ("https://example.com:443/a", "example.com"),
+        ("https://gооgle.com/x", "xn--ggle-55da.com"),  # Cyrillic о: homograph made visible
+        ("http://example.com", None),
+        ("javascript:alert(1)", None),
+        ("https://user:pass@example.com", None),
+        ("https://example.com:8443/a", None),
+        ("https://", None),
+        ("", None),
+        (None, None),
+    ],
+)
+def test_https_host(url, host):
+    assert https_host(url) == host
+
+
+@pytest.mark.parametrize(
+    "url, allowed",
+    [
+        ("https://www.coursera.org/verify/ABC", True),
+        ("https://coursera.org/share/ABC", True),
+        ("https://www.udemy.com/certificate/UC-1/", True),
+        ("https://ude.my/UC-1", True),
+        ("https://coursera.org.evil.example/verify", False),
+        ("https://evilcoursera.org/verify", False),
+        ("http://www.coursera.org/verify/ABC", False),
+    ],
+)
+def test_official_verify_url_allowlist(url, allowed):
+    assert (official_verify_url(url) == url) is allowed
+
+
+# ---------------------------------------------------------------------------
+# Portfolio item validation (API + DB)
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.parametrize(
+    "payload",
+    [
+        {"kind": "CERTIFICATE", "title": "   "},
+        {"kind": "CERTIFICATE", "title": "x" * 121},
+        {"kind": "BADGE", "title": "Rozet"},
+        {"kind": "WORK", "title": "Site", "external_url": "http://ornek.dev"},
+        {"kind": "WORK", "title": "Site", "external_url": "javascript:alert(1)"},
+        {"kind": "CERTIFICATE", "title": "Gelecek", "issued_on": (date.today() + timedelta(days=40)).isoformat()},
+    ],
+)
+def test_create_rejects_invalid_payload(client, owner, payload):
+    user, _ = owner
+    assert client.post(BASE, json=payload, headers=_auth(user)).status_code == 422
+
+
+def test_create_trims_and_clears_blank_optionals(client, owner):
+    user, _ = owner
+    response = client.post(
+        BASE,
+        json={"kind": "CERTIFICATE", "title": "  SQL Temelleri ", "issuer": "  ", "credential_id": " AB-1 "},
+        headers=_auth(user),
+    )
+    assert response.status_code == 201, response.text
+    body = response.json()
+    assert body["title"] == "SQL Temelleri"
+    assert body["issuer"] is None
+    assert body["credential_id"] == "AB-1"
+
+
+def test_patch_cannot_null_required_fields(client, session, owner):
+    user, profile = owner
+    item = PortfolioItem(talent_id=profile.id, kind="WORK", title="Proje")
+    session.add(item)
+    session.flush()
+    for field in ("title", "kind", "show_on_profile"):
+        response = client.patch(f"{BASE}/{item.id}", json={field: None}, headers=_auth(user))
+        assert response.status_code == 422, field
+
+
+def test_patch_clears_optional_field(client, session, owner):
+    user, profile = owner
+    item = PortfolioItem(talent_id=profile.id, kind="WORK", title="Proje", issuer="Kulüp")
+    session.add(item)
+    session.flush()
+    response = client.patch(f"{BASE}/{item.id}", json={"issuer": None}, headers=_auth(user))
+    assert response.status_code == 200
+    assert response.json()["issuer"] is None
+
+
+@pytest.mark.parametrize(
+    "fields",
+    [
+        {"kind": "WORK", "title": "Site", "external_url": "http://ornek.dev"},
+        {"kind": "OTHER", "title": "x"},
+        {"kind": "WORK", "title": ""},
+    ],
+)
+def test_db_constraints_back_the_api_rules(session, owner, fields):
+    _, profile = owner
+    session.add(PortfolioItem(talent_id=profile.id, **fields))
+    with pytest.raises(IntegrityError):
+        with session.begin_nested():
+            session.flush()
+
+
+def test_self_declared_link_shows_host_publicly(client, session, owner):
+    _, profile = owner
+    session.add(
+        PortfolioItem(
+            talent_id=profile.id,
+            kind="WORK",
+            title="Açık kaynak katkı",
+            external_url="https://github.com/ornek/proje",
+            show_on_profile=True,
+        )
+    )
+    session.flush()
+    cert = client.get("/public/talents/portfolyo-sahibi").json()["certificates"][0]
+    assert cert["badge"] == "SELF_DECLARED"
+    assert cert["link_url"] == "https://github.com/ornek/proje"
+    assert cert["link_host"] == "github.com"
+    assert cert["verify_url"] is None
+
+
+# ---------------------------------------------------------------------------
+# "Hakkımda"
+# ---------------------------------------------------------------------------
+
+
+def test_about_round_trip_and_public(client, session, owner):
+    user, profile = owner
+    text = "Bilgisayar mühendisliği 3. sınıf öğrencisiyim.\nVeri görselleştirme ile ilgileniyorum."
+    response = client.patch("/talents/me", json={"about": text}, headers=_auth(user))
+    assert response.status_code == 200, response.text
+    assert response.json()["about"] == text
+    assert client.get("/me", headers=_auth(user)).json()["talent_profile"]["about"] == text
+    assert client.get("/public/talents/portfolyo-sahibi").json()["about"] == text
+
+
+def test_about_limit_and_blank(client, session, owner):
+    user, profile = owner
+    assert client.patch("/talents/me", json={"about": "a" * 1001}, headers=_auth(user)).status_code == 422
+    assert client.patch("/talents/me", json={"about": "a" * 1000}, headers=_auth(user)).status_code == 200
+    response = client.patch("/talents/me", json={"about": "   \n "}, headers=_auth(user))
+    assert response.status_code == 200
+    assert response.json()["about"] is None
+
+
+def test_about_db_check(session, owner):
+    _, profile = owner
+    profile.about = "a" * 1001
+    with pytest.raises(IntegrityError):
+        with session.begin_nested():
+            session.flush()
+
+
+def test_item_limit_per_talent(client, session, owner):
+    """AC-S11: at most MAX_ITEMS_PER_TALENT live items; deleted ones do not count."""
+    user, profile = owner
+    session.add_all(
+        PortfolioItem(talent_id=profile.id, kind="WORK", title=f"Kayıt {n}") for n in range(MAX_ITEMS_PER_TALENT)
+    )
+    session.flush()
+
+    blocked = client.post(BASE, json={"kind": "WORK", "title": "Fazladan"}, headers=_auth(user))
+    assert blocked.status_code == 409
+    assert blocked.json()["code"] == "PORTFOLIO_LIMIT_REACHED"
+
+    first_id = client.get(BASE, headers=_auth(user)).json()["items"][0]["id"]
+    assert client.delete(f"{BASE}/{first_id}", headers=_auth(user)).status_code == 204
+    assert client.post(BASE, json={"kind": "WORK", "title": "Yer açıldı"}, headers=_auth(user)).status_code == 201
diff --git a/backend/tests/test_public_profile.py b/backend/tests/test_public_profile.py
index 4830b18..9411298 100644
--- a/backend/tests/test_public_profile.py
+++ b/backend/tests/test_public_profile.py
@@ -387,6 +387,8 @@ class TestHappyPathPublicProfile:
             "display_name", "headline", "department", "study_year", "city",
             "institution_name", "institution_trust_level",
             "verified_experiences", "skills", "attesting_organization_count",
+            # docs/arastirma-ogrenci-profili.md §4.4: self-declared about + consented certificates
+            "about", "certificates",
         }
         assert response_keys == expected_keys, (
             f"Unexpected keys in response. Expected {expected_keys}, got {response_keys}. "
```
