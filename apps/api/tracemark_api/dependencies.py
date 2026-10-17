"""Owner isolation and CSRF remain mandatory without user accounts."""

from __future__ import annotations

from collections.abc import Generator
from typing import cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .models import Workspace


def get_db(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


def require_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin not in request.app.state.settings.allowed_origins:
        raise HTTPException(403, "This frontend origin is not allowed.")
    if origin is None and request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests require an allowed origin.")


def get_workspace(request: Request) -> Workspace:
    workspace = request.app.state.sessions.resolve(request.cookies.get(request.app.state.settings.cookie_name))
    if workspace is None:
        raise HTTPException(401, "Your private browser workspace has expired. Reload the page to start a new one.")
    return cast(Workspace, workspace)


def require_csrf(request: Request, workspace: Workspace = Depends(get_workspace)) -> None:
    require_origin(request)
    if not request.app.state.sessions.verify_csrf(workspace, request.headers.get("x-csrf-token")):
        raise HTTPException(403, "The workspace security check failed. Reload the page and try again.")
