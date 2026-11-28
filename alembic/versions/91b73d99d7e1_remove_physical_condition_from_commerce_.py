"""remove_physical_condition_from_commerce_product

Revision ID: 91b73d99d7e1
Revises: f6c115453a45
Create Date: 2026-11-28 12:20:36.927547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '91b73d99d7e1'
down_revision: Union[str, Sequence[str], None] = 'f6c115453a45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
