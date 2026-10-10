"""
Pydantic request/response schemas for /auth — never the same class as the ORM model.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Simple format check only — the email-validator package (needed for
# pydantic's EmailStr) is not in requirements.txt and adding it is a
# dependency change requiring separate approval per CLAUDE.md. Uniqueness
# and deliverability are irrelevant here; this just rejects obvious garbage.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

AccountKind = Literal["TALENT", "ORGANIZATION", "INSTITUTION"]


class RegisterRequest(BaseModel):
    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    # docs/API.md §2.1 (revised): account_kind is NOT an authorization
    # grant — it just decides whether an Organization/Institution is
    # created alongside the user, with the caller as its ADMIN. Every
    # account still gets a talent profile regardless of kind.
    account_kind: AccountKind = "TALENT"
    entity_name: str | None = Field(default=None, min_length=1, max_length=200)
    # MERSİS number (16 digits) — only meaningful for ORGANIZATION; stored as
    # organizations.legal_id. Format check only: it proves nothing about the
    # company, the T3 decision stays with the admin queue (docs/DOMAIN.md).
    legal_id: str | None = Field(default=None, pattern=r"^\d{16}$")

    @model_validator(mode="after")
    def _entity_name_required_for_org_or_institution(self) -> "RegisterRequest":
        if self.account_kind != "TALENT" and not self.entity_name:
            raise ValueError("entity_name is required when account_kind is ORGANIZATION or INSTITUTION")
        return self


class RegisterResponse(BaseModel):
    user_id: uuid.UUID


class LoginRequest(BaseModel):
    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user_id: uuid.UUID
    role: str
    email_verified: bool


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)
