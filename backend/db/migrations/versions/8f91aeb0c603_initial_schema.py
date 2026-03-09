"""initial_schema

Revision ID: 8f91aeb0c603
Revises: 
Create Date: 2026-03-08 20:44:21.842040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f91aeb0c603'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "hands",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("hand_id", sa.String, nullable=False, unique=True),
        sa.Column("game_type", sa.String, nullable=False),
        sa.Column("small_blind", sa.Float, nullable=False),
        sa.Column("big_blind", sa.Float, nullable=False),
        sa.Column("table_name", sa.String, nullable=False),
        sa.Column("played_at", sa.String, nullable=False),
        sa.Column("hero_name", sa.String, nullable=True),
        sa.Column("pot", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("rake", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("cash_drop", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("currency", sa.String, nullable=False, server_default="USD"),
        sa.Column("is_walk", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("allin_equity_json", sa.String, nullable=True),
        sa.Column("allin_pot_bb", sa.Float, nullable=True),
        sa.Column("allin_invested_bb", sa.Float, nullable=True),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("hand_id", sa.Integer, sa.ForeignKey("hands.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("seat", sa.Integer, nullable=False),
        sa.Column("stack", sa.Float, nullable=False),
        sa.Column("position", sa.String, nullable=True),
        sa.Column("hole_cards", sa.String, nullable=True),
        sa.Column("net_won", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("pot_won_after_rake", sa.Float, nullable=False, server_default="0.0"),
        sa.UniqueConstraint("hand_id", "name", name="uq_player_hand_name"),
    )
    op.create_table(
        "streets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("hand_id", sa.Integer, sa.ForeignKey("hands.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("street_order", sa.Integer, nullable=False),
        sa.Column("cards", sa.String, nullable=True),
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("street_id", sa.Integer, sa.ForeignKey("streets.id"), nullable=False),
        sa.Column("action_order", sa.Integer, nullable=False),
        sa.Column("player_name", sa.String, nullable=False),
        sa.Column("action_type", sa.String, nullable=False),
        sa.Column("amount", sa.Float, nullable=True),
        sa.Column("is_all_in", sa.Boolean, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("actions")
    op.drop_table("streets")
    op.drop_table("players")
    op.drop_table("hands")
