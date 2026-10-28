"""Add plan_type to companies
Revision ID: a9f4e2b1c3d8
Revises: 540eefc1793f
Create Date: 2026-06-30 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a9f4e2b1c3d8'
down_revision = '540eefc1793f'
branch_labels = None
depends_on = None

def upgrade():
    try:
        op.add_column('companies', sa.Column('plan_type', sa.String(length=50), nullable=True, server_default='pyme'))
    except Exception:
        print('Column plan_type already exists, skipping.')

def downgrade():
    try:
        op.drop_column('companies', 'plan_type')
    except Exception:
        pass
