"""Enterprise Departments — Multi-tenant data containment

This migration:
  1. Creates the ``departments`` table.
  2. Adds ``department_id``, ``user_id``, ``has_web_access`` columns to ``employees``.
  3. Adds ``max_departments``, ``max_employees`` quota columns to ``companies``.

Revision ID: f1a2b3c4d5e6
Revises: c7a68e26f1c6
Create Date: 2026-07-23 08:42:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'c7a68e26f1c6'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Create departments table ────────────────────────────────────────
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('pinecone_namespace', sa.String(length=255), nullable=True),
        sa.Column('restrict_conversations', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['company_id'], ['companies.id'],
            name='departments_company_fk',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_default_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    op.create_index('ix_departments_company_id', 'departments', ['company_id'], unique=False)

    # ── 2. Add columns to employees ───────────────────────────────────────
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('department_id', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('user_id', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'has_web_access',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('0'),
            )
        )
        batch_op.create_foreign_key(
            'employees_department_fk',
            'departments',
            ['department_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_foreign_key(
            'employees_user_fk',
            'users',
            ['user_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index('ix_employees_department_id', ['department_id'], unique=False)

    # ── 3. Add quota columns to companies ─────────────────────────────────
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'max_departments',
                sa.Integer(),
                nullable=False,
                server_default=sa.text('1'),
            )
        )
        batch_op.add_column(
            sa.Column(
                'max_employees',
                sa.Integer(),
                nullable=False,
                server_default=sa.text('10'),
            )
        )


def downgrade():
    # ── 3. Remove quota columns from companies ────────────────────────────
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_column('max_employees')
        batch_op.drop_column('max_departments')

    # ── 2. Remove columns from employees ──────────────────────────────────
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_index('ix_employees_department_id')
        batch_op.drop_constraint('employees_user_fk', type_='foreignkey')
        batch_op.drop_constraint('employees_department_fk', type_='foreignkey')
        batch_op.drop_column('has_web_access')
        batch_op.drop_column('user_id')
        batch_op.drop_column('department_id')

    # ── 1. Drop departments table ─────────────────────────────────────────
    op.drop_index('ix_departments_company_id', table_name='departments')
    op.drop_table('departments')
