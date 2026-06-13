import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models import AuditAction, AuditLog


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def write_audit_log(
    session: AsyncSession,
    *,
    action: AuditAction,
    request: Request,
    admin_user_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        admin_user_id=admin_user_id,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500],
        audit_metadata=metadata,
    )
    session.add(entry)
    await session.flush()
    return entry
