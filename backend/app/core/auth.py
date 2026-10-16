import hmac
from typing import Optional
from fastapi import Request, Header, status
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.core.errors import AppException


class AuthenticatedReviewer(BaseModel):
    reviewer_id: str
    role: str = "reviewer"  # "reviewer" or "admin"


async def get_current_reviewer(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_reviewer_token: Optional[str] = Header(None, alias="X-Reviewer-Token"),
) -> AuthenticatedReviewer:
    """
    Extracts and validates the reviewer authentication token strictly from headers:
      1. Authorization header: "Bearer <token>"
      2. X-Reviewer-Token header: "<token>"

    Query parameter token extraction (?reviewer_token=) is deliberately prohibited
    to prevent sensitive credentials from leaking into server access logs, proxy caches,
    and browser history.

    Derives reviewer identity and role from server-configured credentials using
    constant-time comparison (hmac.compare_digest).
    """
    # If audit authentication is explicitly disabled (e.g. air-gapped demo mode), allow access
    if not settings.AUDIT_AUTH_ENABLED:
        return AuthenticatedReviewer(
            reviewer_id="Local-Demo-Reviewer",
            role="admin",
        )

    token: Optional[str] = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_reviewer_token:
        token = x_reviewer_token.strip()

    if not token:
        raise AppException(
            code="UNAUTHORIZED",
            message=(
                "Authentication required for audit review operations. "
                "Provide an authorization token via 'Authorization: Bearer <token>' "
                "or 'X-Reviewer-Token' header."
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Constant-time token lookup using hmac.compare_digest to prevent timing attacks
    matched_info = None
    for configured_token, info in settings.REVIEWER_TOKENS.items():
        if hmac.compare_digest(configured_token, token):
            matched_info = info
            break

    if not matched_info:
        raise AppException(
            code="INVALID_TOKEN",
            message="Invalid or unrecognized reviewer authentication token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return AuthenticatedReviewer(
        reviewer_id=matched_info["reviewer_id"],
        role=matched_info.get("role", "reviewer"),
    )
