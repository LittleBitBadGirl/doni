from uuid import UUID

from starlette.requests import Request
from starlette.responses import Response

from app.auth.constants import ADMIN_COOKIE_NAME
from app.auth.jwt import decode_access_token
from app.config import get_settings


def set_admin_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        max_age=settings.jwt_expire_hours * 3600,
        path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        path="/",
        secure=settings.app_env == "production",
        samesite="strict",
    )


def get_admin_id_from_request(request: Request) -> UUID | None:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError):
        return None
