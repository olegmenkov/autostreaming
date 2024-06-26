"""fixed columns types

Revision ID: 189889a26650
Revises: a09fb6885fc5
Create Date: 2024-01-19 02:54:31.333848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '189889a26650'
down_revision: Union[str, None] = 'a09fb6885fc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('groups', 'G_id',
               existing_type=sa.UUID(),
               type_=sa.String(length=36),
               existing_nullable=False)
    op.alter_column('groups_obs', 'OBS_id',
               existing_type=sa.UUID(),
               type_=sa.String(length=36),
               existing_nullable=False)
    op.alter_column('obs', 'OBS_id',
               existing_type=sa.UUID(),
               type_=sa.String(length=36),
               existing_nullable=False)
    op.alter_column('schedule', 'OBS_id',
               existing_type=sa.UUID(),
               type_=sa.String(length=36),
               existing_nullable=False)
    op.alter_column('users', 'U_id',
               existing_type=sa.UUID(),
               type_=sa.String(length=36),
               existing_nullable=False)
    op.alter_column('users_obs', 'OBS_id',
               existing_type=sa.UUID(),
               type_=sa.String(length=36),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users_obs', 'OBS_id',
               existing_type=sa.String(length=36),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('users', 'U_id',
               existing_type=sa.String(length=36),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('schedule', 'OBS_id',
               existing_type=sa.String(length=36),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('obs', 'OBS_id',
               existing_type=sa.String(length=36),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('groups_obs', 'OBS_id',
               existing_type=sa.String(length=36),
               type_=sa.UUID(),
               existing_nullable=False)
    op.alter_column('groups', 'G_id',
               existing_type=sa.String(length=36),
               type_=sa.UUID(),
               existing_nullable=False)
    # ### end Alembic commands ###
