"""Authentication and CSRF request dependencies."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .sessions import SessionRecord


async def get_session_record(request: Request) -> SessionRecord:
    token = request.cookies.get(request.app.state.settings.cookie_name)
    record = await request.app.state.sessions.resolve(token)
    if record is None:
        raise HTTPException(status_code=401, detail="authentication required")
    request.state.session_record = record
    return cast(SessionRecord, record)


def get_current_user(
    record: SessionRecord = Depends(get_session_record), session: Session = Depends(get_db)
) -> User:
    try:
        user_id = UUID(record.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="authentication required") from exc
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="authentication required")
    return user


async def require_csrf(request: Request, record: SessionRecord = Depends(get_session_record)) -> None:
    token = request.headers.get("x-csrf-token")
    if not request.app.state.sessions.verify_csrf(record, token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

