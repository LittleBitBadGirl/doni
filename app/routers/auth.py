from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import ADMIN_COOKIE_NAME
from app.auth.cookies import clear_admin_cookie, set_admin_cookie
from app.auth.jwt import create_access_token, decode_access_token
from app.auth.password import verify_password
from app.database import get_db
from app.models import AdminUser, AuditAction
from app.limiter import limiter
from app.services.audit import write_audit_log
from app.templating import base_context, templates

router = APIRouter(tags=["admin-auth"])


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token:
        return False
    return decode_access_token(token) is not None


@router.get("/admin/login", response_class=HTMLResponse, name="admin_login", response_model=None)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            **base_context(),
            "title": "Вход для правления",
            "error": None,
        },
    )


@router.post("/admin/login", response_class=HTMLResponse, name="admin_login_submit", response_model=None)
@limiter.limit("5/15minutes")
async def login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))

    error: str | None = None
    admin: AdminUser | None = None

    if not email or not password:
        error = "Введите email и пароль."
    else:
        admin = await db.scalar(
            select(AdminUser).where(AdminUser.email == email, AdminUser.is_active.is_(True))
        )
        if admin is None or not verify_password(password, admin.password_hash):
            error = "Неверный email или пароль."

    if error:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                **base_context(),
                "title": "Вход для правления",
                "error": error,
                "email": email,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    assert admin is not None
    token = create_access_token(admin.id, admin.email)
    await write_audit_log(
        db,
        action=AuditAction.admin_login,
        request=request,
        admin_user_id=admin.id,
        metadata={"email": admin.email},
    )
    await db.commit()

    response = RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)
    set_admin_cookie(response, token)
    return response


@router.post("/admin/logout", name="admin_logout", response_model=None)
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    clear_admin_cookie(response)
    return response
