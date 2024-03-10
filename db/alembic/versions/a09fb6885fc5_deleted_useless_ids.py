"""deleted useless ids

Revision ID: a09fb6885fc5
Revises: 04c3ac87ccff
Create Date: 2024-01-19 02:30:21.327037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a09fb6885fc5'
down_revision: Union[str, None] = '04c3ac87ccff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('groups', 'G_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('groups', 'id')
    op.alter_column('obs', 'OBS_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('obs', 'id')
    op.alter_column('users', 'U_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('users', 'id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.alter_column('users', 'U_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.add_column('obs', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.alter_column('obs', 'OBS_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.add_column('groups', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.alter_column('groups', 'G_id',
               existing_type=sa.UUID(),
               nullable=True)
    # ### end Alembic commands ###