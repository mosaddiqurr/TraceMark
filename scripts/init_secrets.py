"""Create local-only TraceMark secrets without overwriting configured values."""

from __future__ import annotations

import secrets
from pathlib import Path

TEMPLATE = Path(".env.example")
TARGET = Path(".env")
SECRET_KEYS = {"TRACEMARK_MASTER_KEY", "TRACEMARK_REPORT_KEY", "TRACEMARK_SESSION_PEPPER"}


def main() -> None:
    if not TARGET.exists():
        TARGET.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    lines = TARGET.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    changed = False
    for line in lines:
        name, separator, value = line.partition("=")
        if separator and name in SECRET_KEYS and not value.strip():
            output.append(f"{name}={secrets.token_urlsafe(48)}")
            changed = True
        else:
            output.append(line)
    TARGET.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("Initialized local TraceMark secrets." if changed else "Local secrets already configured.")


if __name__ == "__main__":
    main()

