"""
Certificate check resolve endpoint (PLAN 3.55). Listing lives under
/engagements/{id}/certificate-checks (app/api/engagements.py) — this router
only holds the koordinatör karar (CONFIRMED/REJECTED) action, since it isn't
naturally nested under either /evidence or /engagements by its own id.
"""

import uuid

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.schemas.certificate_check import CertificateCheckResolveRequest, CertificateCheckResponse
from app.services.authorization import Principal
from app.services.audit import log_audit_event
from app.services.certificate_check import CheckNotFoundError, CheckNotPendingError, resolve_certificate_check

router = APIRouter(prefix="/certificate-checks", tags=["certificate-checks"])


@router.post("/{check_id}/resolve", response_model=CertificateCheckResponse)
def resolve_certificate_check_endpoint(
    payload: CertificateCheckResolveRequest,
    check_id: uuid.UUID = Path(..., description="CertificateCheck UUID"),
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> CertificateCheckResponse:
    """
    PLAN 3.55: nihai CONFIRMED/REJECTED kararı — AI bu kararı asla vermez,
    yalnız engagement'ın koordinatörü/supervisor'u verebilir (talent kendi
    talebini görebilir ama karar veremez — scoped_evidence'ın dar istisnası,
    bkz. app/services/certificate_check.py modül docstring'i).

    Errors:
        404 NOT_FOUND: check yok veya principal karar veremez (koordinatör değil)
        409 NOT_PENDING: karar zaten verilmiş
    """
    try:
        check = resolve_certificate_check(
            session, principal, check_id, payload.decision, principal.user_id
        )
    except CheckNotFoundError:
        raise ApiError(404, "NOT_FOUND", "Kayıt bulunamadı.")
    except CheckNotPendingError:
        raise ApiError(409, "NOT_PENDING", "Bu kayıt zaten incelenmiş.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="CERTIFICATE_CHECK_RESOLVED",
        subject_type="certificate_check",
        subject_id=check_id,
        result="SUCCESS",
        metadata={"decision": payload.decision},
    )
    session.commit()
    return CertificateCheckResponse.model_validate(check)
