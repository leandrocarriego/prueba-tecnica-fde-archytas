"""Access control: sessions, credential tokens, the access log and its settings.

Four tables and four columns that turn the identity module from "there are
users with roles" into what the signed spec describes.

`sessions` is the one that replaces something rather than adding: the platform
used to authenticate with a signed token, and a signed token cannot be revoked
when the owner deactivates somebody, nor measure how long they have been idle.

`password_reset_tokens` is dropped and replaced by `credential_tokens`, which
stores the **hash** of the token instead of the token itself and covers both
purposes — invitation and recovery — because they are the same mechanism.

It ends by seeding the three parameters the feature starts with, so a brand-new
installation knows how long a session lasts before anybody touches a setting.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OPERATIONS_SCHEMA = "operations"

# The owner changes these from the parameters screen; identity keeps its own
# projection fed by `BusinessParameterChanged` rather than reading this table.
INITIAL_PARAMETERS: tuple[tuple[str, str, str], ...] = (
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
    # --- a session is a row now, so it can be revoked and touched ---------

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked_reason",
            sa.Enum(
                "LOGOUT",
                "DEACTIVATION",
                "PASSWORD_CHANGED",
                "REACTIVATION",
                name="session_revocation",
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_last_seen_at"), "sessions", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_sessions_token_hash"), "sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    # --- invitation and recovery: one mechanism, two purposes ------------

    op.create_table(
        "credential_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("INVITATION", "PASSWORD_RESET", name="token_purpose"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_credential_tokens_token_hash"), "credential_tokens", ["token_hash"], unique=True
    )
    op.create_index(
        op.f("ix_credential_tokens_user_id"), "credential_tokens", ["user_id"], unique=False
    )

    # --- nothing is discarded, not even a rejected attempt ---------------

    op.create_table(
        "access_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "LOGIN_SUCCEEDED",
                "LOGIN_REJECTED",
                "ACCESS_LOCKED",
                "PERMISSION_DENIED",
                "ACCESS_GRANTED",
                "ACCESS_ROLE_CHANGED",
                "ACCESS_DEACTIVATED",
                "ACCESS_REACTIVATED",
                name="access_event_kind",
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("attempted_email", sa.String(length=255), nullable=True),
        sa.Column("resource", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_events_kind"), "access_events", ["kind"], unique=False)
    op.create_index(
        op.f("ix_access_events_occurred_at"), "access_events", ["occurred_at"], unique=False
    )
    op.create_index(op.f("ix_access_events_user_id"), "access_events", ["user_id"], unique=False)

    # --- identity's own copy of what `operations` owns -------------------

    op.create_table(
        "access_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # --- the token in the clear goes away --------------------------------

    op.drop_index(op.f("ix_password_reset_tokens_token"), table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    # --- what an access needs to be invited, blocked and audited ---------

    op.add_column("users", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    # Every existing account predates the invitation flow, so it already has a
    # password of its own: it is active, not invited.
    op.execute(sa.text("UPDATE users SET activated_at = created_at WHERE activated_at IS NULL"))

    # The phone stops being optional, because it is the only way an invitation
    # or a recovery link reaches anybody. There is no sensible value to invent
    # for a row that lacks one, so the migration says what to fix instead of
    # failing on a constraint nobody can read.
    connection = op.get_bind()
    without_phone = connection.execute(
        sa.text("SELECT count(*) FROM users WHERE phone IS NULL OR phone = ''")
    ).scalar_one()
    if without_phone:
        raise RuntimeError(
            f"{without_phone} usuario(s) sin teléfono. La invitación y la recuperación de clave "
            "van por WhatsApp, así que el teléfono pasa a ser obligatorio: cargá el de cada "
            "persona antes de aplicar esta migración."
        )
    op.alter_column("users", "phone", existing_type=sa.VARCHAR(length=20), nullable=False)

    # --- the values the platform starts with (RF-36, RF-49) --------------

    for key, value, description in INITIAL_PARAMETERS:
        op.execute(
            sa.text(
                f'INSERT INTO "{OPERATIONS_SCHEMA}".parameter (key, value, description) '
                "VALUES (:key, CAST(:value AS jsonb), :description) "
                "ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=key, value=value, description=description)
        )
        op.execute(
            sa.text(
                "INSERT INTO access_settings (key, value, description) "
                "VALUES (:key, CAST(:value AS jsonb), :description) "
                "ON CONFLICT (key) DO NOTHING"
            ).bindparams(key=key, value=value, description=description)
        )


def downgrade() -> None:
    op.execute(
        sa.text(f'DELETE FROM "{OPERATIONS_SCHEMA}".parameter WHERE key = ANY(:keys)').bindparams(
            keys=[key for key, _, _ in INITIAL_PARAMETERS]
        )
    )

    op.alter_column("users", "phone", existing_type=sa.VARCHAR(length=20), nullable=True)
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_attempts")
    op.drop_column("users", "invited_at")
    op.drop_column("users", "activated_at")

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("token", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "used", sa.BOOLEAN(), server_default=sa.text("false"), autoincrement=False, nullable=False
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_token"), "password_reset_tokens", ["token"], unique=True
    )

    op.drop_table("access_settings")
    op.drop_index(op.f("ix_access_events_user_id"), table_name="access_events")
    op.drop_index(op.f("ix_access_events_occurred_at"), table_name="access_events")
    op.drop_index(op.f("ix_access_events_kind"), table_name="access_events")
    op.drop_table("access_events")
    op.drop_index(op.f("ix_credential_tokens_user_id"), table_name="credential_tokens")
    op.drop_index(op.f("ix_credential_tokens_token_hash"), table_name="credential_tokens")
    op.drop_table("credential_tokens")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_token_hash"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_last_seen_at"), table_name="sessions")
    op.drop_table("sessions")

    sa.Enum(name="access_event_kind").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="token_purpose").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="session_revocation").drop(op.get_bind(), checkfirst=True)
