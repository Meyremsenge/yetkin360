"""
Pydantic request/response schemas for /auth — never the same class as the ORM model.
"""

import uuid

from pydantic import BaseModel, Field

# Simple format check only — the email-validator package (needed for
# pydantic's EmailStr) is not in requirements.txt and adding it is a
# dependency change requiring separate approval per CLAUDE.md. Uniqueness
# and deliverability are irrelevant here; this just rejects obvious garbage.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(pattern=_EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


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
