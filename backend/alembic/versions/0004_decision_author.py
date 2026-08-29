"""Who took each decision, in the words the screen shows

RF-32 and RF-36 promise "quién lo decidió", and until now the screen could only
show a number. The name is stored next to the id rather than looked up, for two
reasons: a decision is a historical record — the person who took it does not
stop having taken it when they change their name or leave — and `triage` cannot
read `identity` to render a screen (Artículo IV).

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None

OPERATIONS = "operations"


def upgrade() -> None:
    """Add the author's name to a resolved case and to a learned rule."""
    op.add_column(
        "exception",
        sa.Column("resolved_by_name", sa.String(length=255), nullable=True),
        schema=OPERATIONS,
    )
    op.add_column(
        "resolution_rule",
        sa.Column("created_by_name", sa.String(length=255), nullable=True),
        schema=OPERATIONS,
    )


def downgrade() -> None:
    """Drop them. The ids stay, so nothing that identifies the author is lost."""
    op.drop_column("resolution_rule", "created_by_name", schema=OPERATIONS)
    op.drop_column("exception", "resolved_by_name", schema=OPERATIONS)
