from typing import Optional
from fastapi import Request, Header, Query, status
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
    token_param: Optional[str] = Query(None, alias="reviewer_token"),
) -> AuthenticatedReviewer:
    """
    Extracts and validates the reviewer authentication token from:
      1. Authorization header: "Bearer <token>"
      2. X-Reviewer-Token header
      3. reviewer_token query parameter
    Derives reviewer identity and role from server-configured credentials.
    """
    token: Optional[str] = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_reviewer_token:
        token = x_reviewer_token.strip()
    elif token_param:
        token = token_param.strip()

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

    reviewer_info = settings.REVIEWER_TOKENS.get(token)
    if not reviewer_info:
        raise AppException(
            code="INVALID_TOKEN",
            message="Invalid or unrecognized reviewer authentication token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return AuthenticatedReviewer(
        reviewer_id=reviewer_info["reviewer_id"],
        role=reviewer_info.get("role", "reviewer"),
    )
