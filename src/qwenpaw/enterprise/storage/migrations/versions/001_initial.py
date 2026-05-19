"""初始 schema — enterprise_chats / enterprise_jobs。

Revision ID: 001
Revises: None
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enterprise_chats",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(256), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_enterprise_chats_agent_session",
        "enterprise_chats",
        ["agent_id", "session_id"],
    )
    op.create_index(
        "idx_enterprise_chats_agent_user_channel",
        "enterprise_chats",
        ["agent_id", "user_id", "channel"],
    )

    op.create_table(
        "enterprise_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_enterprise_jobs_agent",
        "enterprise_jobs",
        ["agent_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_enterprise_jobs_agent", table_name="enterprise_jobs")
    op.drop_table("enterprise_jobs")
    op.drop_index(
        "idx_enterprise_chats_agent_user_channel",
        table_name="enterprise_chats",
    )
    op.drop_index(
        "idx_enterprise_chats_agent_session",
        table_name="enterprise_chats",
    )
    op.drop_table("enterprise_chats")
