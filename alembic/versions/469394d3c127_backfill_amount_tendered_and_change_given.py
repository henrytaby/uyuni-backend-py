"""backfill_amount_tendered_and_change_given

Revision ID: 469394d3c127
Revises: e09d0a09bc6f
Create Date: 2026-11-20 14:55:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "469394d3c127"
down_revision: str | Sequence[str] | None = "e09d0a09bc6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill cash fields and sync channel names from commerce_channel."""
    op.execute("""
        UPDATE commerce_sale
        SET amount_tendered = COALESCE(total_collected, 0.0),
            change_given = 0.0
        WHERE amount_tendered IS NULL;
    """)
    op.execute("""
        UPDATE commerce_sale
        SET channel = commerce_channel.name
        FROM commerce_channel
        WHERE commerce_sale.channel_id = commerce_channel.id
          AND commerce_channel.name IS NOT NULL;
    """)
    op.execute("""
        UPDATE commerce_sale
        SET channel = commerce_channel.name,
            channel_id = commerce_channel.id
        FROM commerce_channel
        WHERE commerce_sale.channel_id IS NULL
          AND UPPER(commerce_sale.channel) = UPPER(commerce_channel.code);
    """)
    op.execute("""
        UPDATE commerce_sale
        SET delivery_status = 'PENDING'
        WHERE delivery_status = 'SHIPPED';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
