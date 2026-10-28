"""Add department_id to documents for RAG containment

This migration adds ``department_id`` FK to the ``documents`` table, enabling
per-department RAG namespace isolation in Pinecone.

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-23 08:47:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'g2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('department_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'documents_department_fk',
            'departments',
            ['department_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index('ix_documents_department_id', ['department_id'], unique=False)


def downgrade():
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index('ix_documents_department_id')
        batch_op.drop_constraint('documents_department_fk', type_='foreignkey')
        batch_op.drop_column('department_id')
