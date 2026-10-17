"""Persistent anonymous browser capabilities; plaintext cookies are never stored."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Workspace


class SessionManager:
    def __init__(self, factory: sessionmaker[Session], pepper: str, ttl_seconds: int, max_workspaces: int):
        self.factory = factory
        self._pepper = pepper.encode()
        self.ttl_seconds = ttl_seconds
        self.max_workspaces = max_workspaces

    def token_digest(self, token: str) -> str:
        return hmac.new(self._pepper, token.encode(), hashlib.sha256).hexdigest()

    def resolve(self, token: str | None) -> Workspace | None:
        if not token or len(token) > 128:
            return None
        with self.factory() as session:
            return session.scalar(
                select(Workspace).where(
                    Workspace.token_digest == self.token_digest(token),
                    Workspace.expires_at > time.time(),
                )
            )

    def create(self) -> tuple[str, Workspace]:
        token = secrets.token_urlsafe(32)
        with self.factory() as session:
            session.execute(delete(Workspace).where(Workspace.expires_at <= time.time()))
            if (session.scalar(select(func.count()).select_from(Workspace)) or 0) >= self.max_workspaces:
                raise RuntimeError("workspace_capacity")
            workspace = Workspace(
                token_digest=self.token_digest(token),
                csrf_token=secrets.token_urlsafe(32),
                expires_at=time.time() + self.ttl_seconds,
            )
            session.add(workspace)
            session.commit()
            return token, workspace

    def prune(self) -> None:
        with self.factory() as session:
            session.execute(delete(Workspace).where(Workspace.expires_at <= time.time()))
            session.commit()

    @staticmethod
    def verify_csrf(workspace: Workspace, supplied: str | None) -> bool:
        return bool(supplied and hmac.compare_digest(workspace.csrf_token, supplied))
