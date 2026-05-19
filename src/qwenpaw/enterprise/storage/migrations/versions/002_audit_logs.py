"""增加 enterprise_audit_logs 表及索引。

Revision ID: 002
Revises: 001
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enterprise_audit_logs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("session_id", sa.String(256), nullable=False, server_default=""),
        sa.Column("actor_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("actor_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("resource_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("resource_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("trace_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(256), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_audit_created_at",
        "enterprise_audit_logs",
        ["created_at"],
    )
    op.create_index(
        "idx_audit_tenant_created",
        "enterprise_audit_logs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_audit_actor_created",
        "enterprise_audit_logs",
        ["actor_id", "created_at"],
    )
    op.create_index(
        "idx_audit_event_type_created",
        "enterprise_audit_logs",
        ["event_type", "created_at"],
    )
    op.create_index(
        "idx_audit_request_id",
        "enterprise_audit_logs",
        ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_audit_request_id", table_name="enterprise_audit_logs")
    op.drop_index(
        "idx_audit_event_type_created", table_name="enterprise_audit_logs"
    )
    op.drop_index("idx_audit_actor_created", table_name="enterprise_audit_logs")
    op.drop_index("idx_audit_tenant_created", table_name="enterprise_audit_logs")
    op.drop_index("idx_audit_created_at", table_name="enterprise_audit_logs")
    op.drop_table("enterprise_audit_logs")
