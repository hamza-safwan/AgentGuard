"""v0.2 / v0.3 observability + auth tables (BLUEPRINT-7 Appendix B).

Revision ID: 0002_v0_2_observability
Revises: 0001_initial
Create Date: 2026-05-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic identifiers
revision = "0002_v0_2_observability"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive columns on existing tables
    with op.batch_alter_table("runs") as batch:
        batch.add_column(
            sa.Column("source", sa.String(length=32), nullable=False, server_default="cli")
        )
        batch.add_column(sa.Column("sampling_meta", sa.JSON(), nullable=True))

    with op.batch_alter_table("trace_steps") as batch:
        batch.add_column(sa.Column("parent_step_id", sa.String(length=36), nullable=True))
        batch.add_column(
            sa.Column(
                "source", sa.String(length=32), nullable=False, server_default="adapter"
            )
        )
        batch.add_column(sa.Column("cost_usd", sa.Float(), nullable=True))
        batch.add_column(sa.Column("tokens", sa.JSON(), nullable=True))

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_tokens_project_id", "auth_tokens", ["project_id"])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("agent_name", sa.String(length=255), nullable=True),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("threshold_drop_pct", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("destinations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "alert_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "rule_id",
            sa.String(length=36),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fired_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_alert_events_rule_id_fired_at",
        "alert_events",
        ["rule_id", "fired_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_alert_events_rule_id_fired_at", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_table("alert_rules")
    op.drop_index("ix_auth_tokens_project_id", table_name="auth_tokens")
    op.drop_table("auth_tokens")

    with op.batch_alter_table("trace_steps") as batch:
        batch.drop_column("tokens")
        batch.drop_column("cost_usd")
        batch.drop_column("source")
        batch.drop_column("parent_step_id")

    with op.batch_alter_table("runs") as batch:
        batch.drop_column("sampling_meta")
        batch.drop_column("source")
