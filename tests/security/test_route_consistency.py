from __future__ import annotations

from pathlib import Path

SOURCE_SUFFIXES = {
    ".html",
    ".jinja",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
SOURCE_DIRECTORIES = (
    "apps/api",
    "apps/web/e2e",
    "apps/web/src",
    "docs",
    "packages/watermark_engine/src",
    "scripts",
    "tests",
)


def test_obsolete_protected_output_route_is_not_generated() -> None:
    repository = Path(__file__).resolve().parents[2]
    obsolete_prefix = "/api/v1/" + "protected-outputs/"
    candidates = [path for path in repository.iterdir() if path.is_file()]
    for directory in SOURCE_DIRECTORIES:
        candidates.extend((repository / directory).rglob("*"))

    violations: list[str] = []
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        relative = path.relative_to(repository).as_posix()
        if obsolete_prefix.encode("ascii") in path.read_bytes():
            violations.append(relative)

    assert violations == [], f"obsolete protected-output route found in: {', '.join(sorted(violations))}"
