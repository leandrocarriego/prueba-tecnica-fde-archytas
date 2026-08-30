"""Where a value came from, on the rows that hold a value

RF-33 says a datum loaded entirely by hand offers no "back to the portal
value", and until now the code answered that with `registered_by_rule_id` —
which says which learned rule incorporated a product (RF-37) and is a different
question altogether. A product that arrived in an ordinary daily list has no
rule either, so the column read every one of them as typed by hand.

The question is answered here instead, by the rows that hold the value: whether
what is written there was reported by the portal or written by this platform.
It reuses `core.price_source`, the enum `core.price_point` already uses, rather
than declaring a second two-value twin of it.

`core.product_price` and not only `core.product` on purpose: the next daily
list re-prices a product a person loaded by hand, and from that morning on the
amount *is* the portal's even though the product never was.

**What the existing rows get, and why.** Both columns land as `PORTAL`. Every
product in this database arrived in a list — the catalog was seeded by one
(RF-02) and only grows by a decision after that — so `PORTAL` is not a guess
for the vast majority of them, and `registered_by_rule_id` cannot single out
the rest: it is null both for a product a list brought and for one a person
incorporated with no rule saved. Defaulting to `SYSTEM` to be careful would be
the worse mistake by far: it would tell the platform that no value in the
catalog was ever reported by the portal, so no correction would keep what the
portal said (RF-25) and the next list would overwrite every manual correction
in silence (RF-28). The prices settle themselves within a day either way, since
the next list stamps each one with the truth.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE = "core"

# Created in 0002 for `core.price_point`. Declared here with `create_type=False`
# so this migration reuses it instead of trying to create it a second time.
PRICE_SOURCE = postgresql.ENUM(
    "PORTAL", "SYSTEM", name="price_source", schema=CORE, create_type=False
)


def upgrade() -> None:
    """Give the product and its price in force the flag RF-33 needs."""
    for table in ("product", "product_price"):
        op.add_column(
            table,
            sa.Column("source", PRICE_SOURCE, server_default="PORTAL", nullable=False),
            schema=CORE,
        )


def downgrade() -> None:
    """Drop both columns. The enum stays: `core.price_point` still uses it."""
    for table in ("product_price", "product"):
        op.drop_column(table, "source", schema=CORE)
