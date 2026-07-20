"""Administrative CLI for database migrations and deterministic demo seeding."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password, normalize_email
from .database import make_engine
from .enums import UserRole
from .models import User
from .settings import load_settings


def _alembic_config() -> Config:
    candidates = (
        Path.cwd() / "apps" / "api" / "alembic.ini",
        Path.cwd() / "alembic.ini",
        Path(__file__).resolve().parents[1] / "alembic.ini",
    )
    for path in candidates:
        if path.is_file():
            config = Config(str(path))
            config.set_main_option("script_location", str(path.parent / "alembic"))
            config.set_main_option("sqlalchemy.url", load_settings().database_url)
            return config
    raise RuntimeError("could not locate apps/api/alembic.ini")


def migrate() -> None:
    command.upgrade(_alembic_config(), "head")
    print("TraceMark database is at the latest migration.")


def seed() -> None:
    settings = load_settings()
    email = normalize_email(os.getenv("TRACEMARK_DEMO_EMAIL", "demo@tracemark.local"))
    password = os.getenv("TRACEMARK_DEMO_PASSWORD", "TraceMark-Demo-Only-2026!")
    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session:
            existing = session.scalar(select(User).where(User.email == email))
            if existing is None:
                session.add(
                    User(
                        email=email,
                        display_name="TraceMark Demo",
                        password_hash=hash_password(password),
                        role=UserRole.USER,
                        is_active=True,
                    )
                )
                session.commit()
                print(f"Created demonstration account: {email}")
            else:
                print(f"Demonstration account already exists: {email}")
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tracemark_api.cli")
    parser.add_argument("command", choices=("migrate", "seed"))
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    else:
        seed()


if __name__ == "__main__":
    main()