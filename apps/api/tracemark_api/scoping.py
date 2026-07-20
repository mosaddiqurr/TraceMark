"""Reusable owner-scoped lookup helpers to make IDOR-safe access the default."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


class OwnedModel(Protocol):
    id: UUID
    owner_id: UUID


def get_owned[ModelT: OwnedModel](
    session: Session, model: type[ModelT], resource_id: UUID, owner_id: UUID
) -> ModelT | None:
    """Return a resource only when both its opaque ID and owner match."""

    return session.scalar(select(model).where(
        model.id == resource_id, model.owner_id == owner_id  # type: ignore[arg-type]
    ))

