"""Initial migration

Revision ID: 04c3ac87ccff
Revises: 
Create Date: 2024-01-19 02:11:51.758166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04c3ac87ccff'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('group_membership',
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('M_admin', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('group_id', 'user_id')
    )
    op.create_table('groups',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('G_id', sa.UUID(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('groups_obs',
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('OBS_id', sa.UUID(), nullable=False),
    sa.Column('GO_name', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('group_id', 'OBS_id')
    )
    op.create_table('obs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('OBS_id', sa.UUID(), nullable=True),
    sa.Column('OBS_ip', sa.String(length=40), nullable=False),
    sa.Column('OBS_port', sa.Integer(), nullable=False),
    sa.Column('OBS_pswd', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('schedule',
    sa.Column('OBS_id', sa.UUID(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('S_start', sa.Date(), nullable=False),
    sa.Column('S_end', sa.Date(), nullable=False),
    sa.PrimaryKeyConstraint('OBS_id', 'group_id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('U_id', sa.UUID(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users_obs',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('OBS_id', sa.UUID(), nullable=False),
    sa.Column('UO_name', sa.String(length=40), nullable=False),
    sa.Column('UO_access_grant', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('user_id', 'OBS_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users_obs')
    op.drop_table('users')
    op.drop_table('schedule')
    op.drop_table('obs')
    op.drop_table('groups_obs')
    op.drop_table('groups')
    op.drop_table('group_membership')
    # ### end Alembic commands ###
