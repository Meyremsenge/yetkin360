"""
Shared HTTP error shape per docs/API.md §1.4: {code, message, request_id}.
"""

import uuid

from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(
        self, status_code: int, code: str, message: str, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "request_id": str(uuid.uuid4())},
            headers=headers,
        )
