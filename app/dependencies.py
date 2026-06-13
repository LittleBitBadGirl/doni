from uuid import UUID

from fastapi import HTTPException, Request, status

from app.auth.cookies import get_admin_id_from_request


def require_admin(request: Request) -> UUID:
    admin_id = get_admin_id_from_request(request)
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация администратора",
        )
    return admin_id
