"""What the portal said is never rewritten.

> `raw` guarda lo extraído tal cual llegó. Lo inmutable es **lo extraído**:
> el contenido, su hash, su tipo y el momento en que llegó.

`CONSTITUTION.md`, Artículo III. The article allows a bookkeeping column that
records that the pipeline already read a document — `normalized_at` — and
nothing else. That distinction is the whole reason this file exists: a rule
whose edge is "well, this column is different" is an interpretation until a
test enumerates which columns it means.

Until 2026-08-29 the invariant was held by absence — the repository simply had
no `update` — and by prose in `plan.md`. Absence is not a rule: the day somebody
needs one write, nothing tells them where the line is.

The check is static, so it also catches a write in code no test exercises yet.
"""

import ast
from pathlib import Path

import pytest

import app

APP_ROOT = Path(app.__file__).resolve().parent
RAW_REPOSITORY = APP_ROOT / "modules" / "portal" / "repository.py"

# What the portal delivered. None of it may ever be assigned outside the insert.
EXTRACTED_COLUMNS: frozenset[str] = frozenset(
    {"content", "content_hash", "content_type", "fetched_at"}
)

# The only method allowed to write them, because it is the one that creates the
# row in the first place.
CREATOR = "insert"


def functions_of(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function defined in a module, methods included."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def attributes_assigned_in(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """The attribute names this function writes: `x.name = ...`."""
    written: set[str] = set()
    for node in ast.walk(function):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            targets = [node.target]
        written.update(target.attr for target in targets if isinstance(target, ast.Attribute))
    return written


class TestTheExtractedDocumentIsNeverRewritten:
    """The repository over `raw` is append-only where it matters."""

    def test_no_function_but_the_insert_writes_what_the_portal_delivered(self) -> None:
        """A bookkeeping column is allowed; the document itself is not."""
        offenders: dict[str, set[str]] = {}
        for function in functions_of(RAW_REPOSITORY):
            if function.name == CREATOR:
                continue
            forbidden = attributes_assigned_in(function) & EXTRACTED_COLUMNS
            if forbidden:
                offenders[function.name] = forbidden

        assert offenders == {}, (
            "These write what the portal delivered, and only `insert` may: "
            f"{offenders}. Artículo III — a correction belongs on the way to "
            "`staging`, never on `raw`."
        )

    @pytest.mark.parametrize("forbidden", ["update", "delete"])
    def test_the_repository_offers_no_blanket_write(self, forbidden: str) -> None:
        """No general-purpose write: each one has to be narrow and named."""
        names = {function.name for function in functions_of(RAW_REPOSITORY)}
        assert forbidden not in names, (
            f"`RawDocumentRepository.{forbidden}` would make Artículo III depend "
            "on whoever calls it. A write over `raw` has to say what it writes."
        )
