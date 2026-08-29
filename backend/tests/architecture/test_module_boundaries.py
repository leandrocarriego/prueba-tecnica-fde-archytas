"""The boundary that holds the modular monolith together.

> A module never imports another module. It communicates through events.

Every file of a module — its `service.py` included — is private to it. What one
module publishes for another to consume is a domain event in
`app.shared.events`, and the two sides never learn each other's name.

The single exception is `dependencies.py`. It is HTTP authorization composition
over a service, and authorization is a synchronous question the request has to
answer before the handler runs — an event cannot answer it. `app.main` and other
modules' routers may mount it; nothing else crosses.

The rule is documented in `CONSTITUTION.md` (Artículo IV) and `ARCHITECTURE.md`,
and enforced here: documentation does not fail a build, a test does.

The check is static (it reads the imports, it does not run them), so it also
catches a violation in code no test exercises yet.
"""

import ast
from pathlib import Path

import pytest

import app

APP_ROOT = Path(app.__file__).resolve().parent
MODULES_ROOT = APP_ROOT / "modules"
SHARED_ROOT = APP_ROOT / "shared"

MODULES_PACKAGE = "app.modules"

# The only file of a module that another module may import. Everything else —
# `service`, `schemas`, `repository`, `models`, `tasks` — is private.
CROSS_MODULE_ALLOWED: frozenset[str] = frozenset({"dependencies"})


def python_files(root: Path) -> list[Path]:
    """Return every Python source file under a directory."""
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def package_of(path: Path) -> str:
    """Return the dotted package a file belongs to (`app.modules.identity`)."""
    return ".".join(("app", *path.resolve().relative_to(APP_ROOT).parent.parts))


def imported_modules(path: Path) -> set[str]:
    """Return every dotted name a file imports.

    `from app.modules.identity import models` and
    `from app.modules.identity.models import User` both yield
    `app.modules.identity.models`, so the caller only has to compare strings.
    Relative imports are resolved against the file's own package.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package_of(path).split(".")
                base = ".".join(parts[: len(parts) - node.level + 1])
                prefix = f"{base}.{node.module}" if node.module else base
            else:
                prefix = node.module or ""
            found.add(prefix)
            # `from package import submodule` names the submodule in `names`.
            found.update(f"{prefix}.{alias.name}" for alias in node.names)

    return found


def most_specific(names: set[str]) -> set[str]:
    """Drop the names that are only a prefix of another name in the set.

    `from app.modules.identity import dependencies` reports both
    `app.modules.identity` and `app.modules.identity.dependencies`. Keeping only
    the longest form is what stops the legitimate one from being read as a bare
    import of the whole package.
    """
    return {
        name
        for name in names
        if not any(other != name and other.startswith(f"{name}.") for other in names)
    }


def module_names() -> list[str]:
    """Return the name of every domain module (`identity`, `operations`, ...)."""
    return sorted(
        path.name
        for path in MODULES_ROOT.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    )


def violations_in(path: Path, owner: str) -> list[str]:
    """Return the imports this file makes into a module other than its own."""
    others = {name for name in module_names() if name != owner}
    offences: set[str] = set()

    for name in most_specific(imported_modules(path)):
        parts = name.split(".")
        if len(parts) < 3 or parts[:2] != ["app", "modules"] or parts[2] not in others:
            continue
        target = ".".join(parts[:4])
        if len(parts) > 3 and parts[3] in CROSS_MODULE_ALLOWED:
            continue
        offences.add(target)

    return sorted(offences)


@pytest.mark.unit
class TestModuleBoundaries:
    """No module reaches into another module. They publish events instead."""

    def test_there_are_modules_to_check(self) -> None:
        """A refactor that moves or renames `app/modules/` must not silence this file."""
        assert MODULES_ROOT.is_dir()
        assert module_names()

    def test_no_module_imports_another_module(self) -> None:
        """A module states what happened; it does not call a neighbour.

        An import is a compile-time dependency on someone else's shape: the
        owning module can no longer rename a method, change a signature or split
        a service without breaking code it does not own. An event carries facts,
        not references, and leaves both sides free to change.
        """
        # Arrange
        offences: list[str] = []

        # Act
        for module in module_names():
            for path in python_files(MODULES_ROOT / module):
                for target in violations_in(path, module):
                    relative = path.relative_to(APP_ROOT.parent)
                    offences.append(f"{relative} imports {target}")

        # Assert
        assert not offences, (
            "A module imported another module. Publish a domain event from "
            "app.shared.events and subscribe to it in handlers.py instead:\n  "
            + "\n  ".join(offences)
        )

    def test_authorization_is_the_only_thing_that_crosses(self) -> None:
        """The exception is narrow on purpose, and stays narrow.

        `dependencies.py` is allowed across because a request cannot be
        authorized by an event: the answer is needed before the handler runs.
        This pins the exception to that one filename, so widening it takes an
        explicit edit here rather than a convenient import somewhere.
        """
        assert frozenset({"dependencies"}) == CROSS_MODULE_ALLOWED

    def test_shared_does_not_import_any_module(self) -> None:
        """`app/shared/` is the kernel: it is depended upon, it does not depend.

        This is what keeps the event catalog honest. `app.shared.events` is
        imported by every module, so a single import in the other direction
        would make the bus a back door into whichever module it reached.
        """
        # Arrange
        offences: list[str] = []

        # Act
        for path in python_files(SHARED_ROOT):
            for imported in sorted(imported_modules(path)):
                if imported.startswith(MODULES_PACKAGE):
                    offences.append(f"{path.relative_to(APP_ROOT.parent)} imports {imported}")

        # Assert
        assert not offences, "app/shared/ must not depend on app/modules/:\n  " + "\n  ".join(
            offences
        )

    def test_the_check_catches_a_real_violation(self, tmp_path: Path) -> None:
        """The detector itself is tested: a passing suite must mean something.

        A boundary test that cannot fail is worse than no boundary test, so this
        feeds it a file that breaks the rule and expects it to be caught. The
        offending file is written outside `app/`, so the check is exercised
        without the suite ever writing into the application.
        """
        # Arrange
        offender = tmp_path / "_boundary_probe.py"
        offender.write_text(
            "from app.modules.identity.service import IdentityService\n"
            "from app.modules.identity.models import User\n"
            "from app.modules.identity import repository\n"
            "import app.modules.identity\n",
            encoding="utf-8",
        )

        # Act
        found = violations_in(offender, owner="operations")

        # Assert
        assert found == [
            "app.modules.identity.models",
            "app.modules.identity.repository",
            "app.modules.identity.service",
        ]

    def test_the_check_lets_authorization_through(self, tmp_path: Path) -> None:
        """Both spellings of the allowed import must pass, or routes cannot authorize."""
        # Arrange
        allowed = tmp_path / "_dependencies_probe.py"
        allowed.write_text(
            "from app.modules.identity.dependencies import get_current_user, require_roles\n"
            "from app.modules.identity import dependencies\n",
            encoding="utf-8",
        )

        # Act
        found = violations_in(allowed, owner="operations")

        # Assert
        assert found == []
