"""
Certificate check request/response schemas (PLAN 3.55).

AI'nin çıkardığı alanlar (provider/credential_id/verify_url/extracted_name/
name_match) hiçbir zaman bir "doğrulandı" iddiası taşımaz — decision alanı
PENDING/CONFIRMED/REJECTED'tır ve yalnız koordinatör tarafından değiştirilir.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CertificateCheckResponse(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    status: str  # PENDING | DONE | FAILED
    provider: str | None
    credential_id: str | None
    verify_url: str | None
    qr_raw_data: str | None
    extracted_name: str | None
    name_match: bool | None
    page_name: str | None
    page_match: bool | None
    decision: str  # PENDING | CONFIRMED | REJECTED
    decided_by_user_id: uuid.UUID | None
    decided_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class CertificateCheckListResponse(BaseModel):
    items: list[CertificateCheckResponse]


class CertificateCheckResolveRequest(BaseModel):
    decision: Literal["CONFIRMED", "REJECTED"]
