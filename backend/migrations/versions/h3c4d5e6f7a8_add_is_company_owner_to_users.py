"""add_is_company_owner_to_users

Revision ID: h3c4d5e6f7a8
Revises: g2b3c4d5e6f7
Create Date: 2026-08-29

Adds the `is_company_owner` boolean column to the `users` table.
Also performs a one-time back-fill: the earliest user of each company
(the one who registered it) is marked as owner automatically.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision = 'h3c4d5e6f7a8'
down_revision = 'g2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    cols = [c['name'] for c in inspector.get_columns('users')]
    
    # 1. Add the column idempotently if it does not already exist
    if 'is_company_owner' not in cols:
        op.add_column(
            'users',
            sa.Column(
                'is_company_owner',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # 2. Back-fill: mark the earliest admin user per company as the owner.
    rows = conn.execute(
        sa.text(
            """
            SELECT MIN(id) AS uid
            FROM   users
            WHERE  role = 'admin'
              AND  company_id IS NOT NULL
            GROUP  BY company_id
            """
        )
    ).fetchall()

    owner_ids = [row[0] for row in rows if row[0] is not None]

    if owner_ids:
        # Mark them as owners (use tuple for MySQL IN clause)
        conn.execute(
            sa.text(
                f"UPDATE users SET is_company_owner = TRUE WHERE id IN ({','.join(str(i) for i in owner_ids)})"
            )
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    cols = [c['name'] for c in inspector.get_columns('users')]
    if 'is_company_owner' in cols:
        op.drop_column('users', 'is_company_owner')
