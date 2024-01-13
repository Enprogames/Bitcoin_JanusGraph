"""Added time to Block

Revision ID: da5e52e8be3b
Revises: 10c54f910d6f
Create Date: 2024-01-13 04:08:00.696378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da5e52e8be3b'
down_revision: Union[str, None] = '10c54f910d6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('blocks', sa.Column('timestamp', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('blocks', 'timestamp')
    # ### end Alembic commands ###