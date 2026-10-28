"""merge multiple heads

Revision ID: 4dd1f904a7a4
Revises: aa89d849cb15, g2b3c4d5e6f7
Create Date: 2026-07-30 13:41:53.378064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4dd1f904a7a4'
down_revision = ('aa89d849cb15', 'g2b3c4d5e6f7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
