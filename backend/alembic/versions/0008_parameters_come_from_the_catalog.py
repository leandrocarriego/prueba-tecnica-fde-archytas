"""The starting values move out of the tables and into the catalog

`operations.parameter` changes meaning with this feature: it used to be *the
list of parameters*, and it becomes *the list of values the owner changed*.
What a parameter is, what it starts at and how far it may move is now declared
in `app/shared/parameters.py`, and a parameter nobody touched has no row at all
(RF-04).

Migration 0003 seeded three access parameters, back when a row was the only way
a parameter could exist. Two of them — the failed-attempt limit and the lockout
— are **not** in the catalog: they keep working from the constants in
`identity`, and their rows are removed because nothing can reach them any more.
The third, the idle timeout, is in the catalog, and its starting value is now
**60 minutes**: the signed spec of this feature says one hour where 002 had
said eight, and the owner moves it from the panel either way.

0003 wrote each of those rows in **two** tables, so this migration removes them
from two. `operations.parameter` is what the panel reads; `access_settings` is
`identity`'s own copy, and `IdentityService._setting` consults it *before*
falling back to the catalog. Clearing only the first would leave the panel
saying 60 while the platform went on closing sessions at eight hours — a number
on the screen that the system does not obey.

Every delete is conditional on the row still holding the value 0003 wrote. A
value somebody actually chose is a decision, and this migration does not get to
overrule it.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# key, the value 0003 seeded and the sentence it wrote beside it. Anything else
# in the row was chosen by a person and stays.
SEEDED: tuple[tuple[str, str, str], ...] = (
    (
        "access.session_idle_minutes",
        "480",
        "Minutos sin uso después de los cuales se cierra la sesión y hay que volver a entrar.",
    ),
    (
        "access.max_failed_attempts",
        "5",
        "Intentos fallidos seguidos que bloquean temporalmente un acceso.",
    ),
    (
        "access.lockout_minutes",
        "15",
        "Minutos que dura el bloqueo de un acceso después de superar los intentos fallidos.",
    ),
)


def upgrade() -> None:
    """Drop the seeded rows that nobody ever changed, from both tables.

    The two statements are spelled out rather than looped over a list of table
    names: `access_settings` is not in the `operations` schema, and a migration
    that names its tables in its own SQL can be read for what it touches.
    """
    for key, seeded, _ in SEEDED:
        op.execute(
            sa.text(
                'DELETE FROM "operations".parameter '
                "WHERE key = :key AND CAST(value AS text) = :seeded"
            ).bindparams(key=key, seeded=seeded)
        )
        op.execute(
            sa.text(
                "DELETE FROM access_settings WHERE key = :key AND CAST(value AS text) = :seeded"
            ).bindparams(key=key, seeded=seeded)
        )


def downgrade() -> None:
    """Put them back in both tables, with the values 0003 wrote.

    `ON CONFLICT DO NOTHING`: if the owner set one of them in the meantime, the
    row is already there and holds a decision this must not overwrite.
    """
    for key, seeded, description in SEEDED:
        op.execute(
            sa.text(
                'INSERT INTO "operations".parameter (key, value, description) '
                "VALUES (:key, CAST(:seeded AS jsonb), :description) "
                "ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=key, seeded=seeded, description=description)
        )
        op.execute(
            sa.text(
                "INSERT INTO access_settings (key, value, description) "
                "VALUES (:key, CAST(:seeded AS jsonb), :description) "
                "ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=key, seeded=seeded, description=description)
        )
