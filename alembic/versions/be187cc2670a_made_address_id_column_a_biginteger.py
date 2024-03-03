"""Made address id column a biginteger

Revision ID: be187cc2670a
Revises: fbc2e0a25168
Create Date: 2024-01-23 18:18:45.634628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be187cc2670a'
down_revision: Union[str, None] = 'fbc2e0a25168'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('address_owner_association', 'address_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('addresses', 'id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               autoincrement=True,
               existing_server_default=sa.text("nextval('addresses_id_seq'::regclass)"))
    op.alter_column('outputs', 'index_in_tx',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('outputs', 'value',
               existing_type=sa.BIGINT(),
               nullable=False)
    op.alter_column('outputs', 'tx_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('outputs', 'address_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True)
    op.alter_column('outputs', 'valid',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('outputs', 'valid',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('outputs', 'address_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('outputs', 'tx_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('outputs', 'value',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.alter_column('outputs', 'index_in_tx',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('addresses', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False,
               autoincrement=True,
               existing_server_default=sa.text("nextval('addresses_id_seq'::regclass)"))
    op.alter_column('address_owner_association', 'address_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    # ### end Alembic commands ###