from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import hash_password, normalize_email, verify_password
from ..database import get_db
from ..dependencies import get_current_user, get_session_record, require_csrf
from ..logging_config import correlation_id_var
from ..models import AuditEvent, User, UserSession
from ..schemas import LoginRequest, RegisterRequest, SessionResponse, UserView
from ..sessions import SessionRecord

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY_PASSWORD_HASH: str | None = None


def _dummy_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = hash_password("not-a-real-password-credential")
    return _DUMMY_PASSWORD_HASH


def _set_cookie(response: Response, request: Request, token: str) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


async def _issue_session(
    user: User, request: Request, response: Response, session: Session
) -> SessionResponse:
    token, csrf_token, record = await request.app.state.sessions.create(user.id)
    session.add(
        UserSession(
            user_id=user.id,
            token_digest=request.app.state.sessions.token_digest(token),
            expires_at=datetime.fromtimestamp(record.expires_at, UTC),
            user_agent_hint=request.headers.get("user-agent", "")[:160] or None,
        )
    )
    session.add(
        AuditEvent(
            actor_user_id=user.id,
            action="session.created",
            resource_type="user",
            resource_id=user.id,
            correlation_id=correlation_id_var.get(),
        )
    )
    session.commit()
    _set_cookie(response, request, token)
    return SessionResponse(user=UserView.model_validate(user), csrf_token=csrf_token)


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, request: Request, response: Response, session: Session = Depends(get_db)
) -> SessionResponse:
    try:
        email = normalize_email(payload.email)
        encoded = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = User(email=email, display_name=payload.display_name.strip(), password_hash=encoded)
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="an account with this email already exists") from exc
    return await _issue_session(user, request, response, session)


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response, session: Session = Depends(get_db)
) -> SessionResponse:
    client = request.client.host if request.client else "unknown"
    identity = hashlib.sha256(f"{client}:{payload.email.casefold()}".encode()).hexdigest()
    if not await request.app.state.rate_limiter.allow(f"login:{identity}", 10, 300):
        raise HTTPException(status_code=429, detail="too many authentication attempts")
    try:
        email = normalize_email(payload.email)
    except ValueError:
        email = "invalid@example.invalid"
    user = session.scalar(select(User).where(User.email == email))
    encoded = user.password_hash if user else _dummy_hash()
    valid = verify_password(payload.password, encoded)
    if user is None or not user.is_active or not valid:
        raise HTTPException(status_code=401, detail="invalid email or password")
    return await _issue_session(user, request, response, session)


@router.get("/session", response_model=SessionResponse)
async def current_session(
    user: User = Depends(get_current_user),
    record: SessionRecord = Depends(get_session_record),
) -> SessionResponse:
    return SessionResponse(user=UserView.model_validate(user), csrf_token=record.csrf_token)

@router.get("/me", response_model=UserView)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def logout(
    request: Request,
    response: Response,
    record: SessionRecord = Depends(get_session_record),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    token = request.cookies.get(request.app.state.settings.cookie_name)
    await request.app.state.sessions.delete(token)
    if token:
        digest = request.app.state.sessions.token_digest(token)
        row = session.scalar(select(UserSession).where(UserSession.token_digest == digest))
        if row is not None:
            row.revoked_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            actor_user_id=user.id,
            action="session.revoked",
            resource_type="user",
            resource_id=user.id,
            correlation_id=correlation_id_var.get(),
        )
    )
    session.commit()
    response.delete_cookie(request.app.state.settings.cookie_name, path="/")
    del record

