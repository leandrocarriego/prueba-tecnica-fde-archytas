#!/usr/bin/env python
"""Check that every command file has parseable YAML frontmatter.

A command whose frontmatter does not parse is not rejected by the tool that
reads it — it is **silently ignored**. That is how eleven of the thirteen
commands in this repository stopped existing without anyone noticing: their
description said `(argumento: 001-portal-extraction)`, and a ": " inside an
unquoted YAML scalar makes the parser read a mapping where none can be.

So this is not a style check. It is the difference between a command that is
there and one that is not, and it belongs in the same place as the other rules
the project calls automatic (`CONSTITUTION.md`).

Usage:
    scripts/validate_command_frontmatter.py [path ...]

With no arguments it checks every `.md` under `.claude/commands/`. Pre-commit
passes the changed files instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / ".claude" / "commands"

DELIMITER = "---"


def frontmatter_of(text: str) -> str | None:
    """Return the raw frontmatter block, or None when the file has none."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == DELIMITER:
            return "\n".join(lines[1:index])
    return None


def problems_with(path: Path) -> list[str]:
    """Return every reason this file would not register as a command."""
    text = path.read_text(encoding="utf-8")

    raw = frontmatter_of(text)
    if raw is None:
        return ["no tiene frontmatter delimitado por `---`"]

    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        detail = str(error).splitlines()[0]
        return [
            f"el frontmatter no es YAML valido: {detail}",
            'si el texto lleva ": " (por ejemplo "(argumento: 001-...)"), entrecomillalo',
        ]

    if not isinstance(parsed, dict):
        return ["el frontmatter no es un mapeo de claves"]

    description = parsed.get("description")
    if description is None:
        return ["le falta `description`, que es lo que se muestra en el menu"]
    if not isinstance(description, str) or not description.strip():
        return ["`description` tiene que ser un texto no vacio"]

    return []


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or sorted(DEFAULT_DIR.glob("*.md"))
    paths = [p for p in paths if p.suffix == ".md" and p.is_file()]

    if not paths:
        print("frontmatter: no hay comandos que revisar")
        return 0

    failed = 0
    for path in paths:
        issues = problems_with(path)
        if issues:
            failed += 1
            print(f"  ✗ {path}")
            for issue in issues:
                print(f"      {issue}")

    if failed:
        print(f"\nfrontmatter: {failed} de {len(paths)} no se registrarian como comando.")
        return 1

    print(f"frontmatter: {len(paths)} comando(s) OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
