"""add agency and modular marketplace tables and columns

Revision ID: e8f1a2b3c4d5
Revises: b5e1f2a3c4d0
Create Date: 2026-09-08 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = 'e8f1a2b3c4d5'
down_revision = 'b5e1f2a3c4d0'
branch_labels = None
depends_on = None


def _table_exists(conn, table_name):
    inspector = sa_inspect(conn)
    return table_name in inspector.get_table_names()


def _column_exists(conn, table_name, column_name):
    inspector = sa_inspect(conn)
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in cols


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    # 1. Update users role enum in MySQL/MariaDB
    if dialect == 'mysql':
        try:
            op.execute(sa.text(
                "ALTER TABLE users MODIFY COLUMN role "
                "ENUM('SUPER_ADMIN','AGENCY','ADMIN','MANAGER','EMPLOYEE') NOT NULL DEFAULT 'ADMIN'"
            ))
        except Exception as e:
            print(f"Warning updating users role enum: {e}")

    # 2. Add columns to companies
    if _table_exists(conn, 'companies'):
        if not _column_exists(conn, 'companies', 'agency_max_companies'):
            op.add_column('companies', sa.Column('agency_max_companies', sa.Integer(), nullable=False, server_default='0'))
        if not _column_exists(conn, 'companies', 'max_agents'):
            op.add_column('companies', sa.Column('max_agents', sa.Integer(), nullable=False, server_default='3'))

    # 3. Create agency_company_access table
    if not _table_exists(conn, 'agency_company_access'):
        op.create_table(
            'agency_company_access',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('agency_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('role_in_client', sa.String(50), nullable=False, server_default='admin'),
            sa.Column('monthly_fee', sa.Float(), nullable=False, server_default='99.0'),
            sa.Column('monthly_credits', sa.Integer(), nullable=False, server_default='5000'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('status', sa.String(50), nullable=True, server_default='active'),
            sa.Column('invite_token', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
    else:
        if not _column_exists(conn, 'agency_company_access', 'status'):
            op.add_column('agency_company_access', sa.Column('status', sa.String(50), nullable=True, server_default='active'))
        if not _column_exists(conn, 'agency_company_access', 'invite_token'):
            op.add_column('agency_company_access', sa.Column('invite_token', sa.String(255), nullable=True))

    # 4. Create modular_assets table
    if not _table_exists(conn, 'modular_assets'):
        op.create_table(
            'modular_assets',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('slug', sa.String(100), unique=True, nullable=False, index=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('asset_type', sa.Enum('BLOG_MODULE', 'ECOMMERCE_MODULE', 'LANDING_SUITE', 'CUSTOM_ASSET', name='assettype'), nullable=False, server_default='BLOG_MODULE'),
            sa.Column('version', sa.String(50), nullable=False, server_default='1.0.0'),
            sa.Column('price_usd', sa.Float(), nullable=False, server_default='49.0'),
            sa.Column('credits_cost', sa.Integer(), nullable=False, server_default='500'),
            sa.Column('zip_filename', sa.String(255), nullable=True),
            sa.Column('zip_url', sa.String(500), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
            sa.Column('features', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # 5. Create asset_licenses table
    if not _table_exists(conn, 'asset_licenses'):
        op.create_table(
            'asset_licenses',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('license_key', sa.String(128), unique=True, nullable=False, index=True),
            sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
            sa.Column('asset_id', sa.Integer(), sa.ForeignKey('modular_assets.id'), nullable=False, index=True),
            sa.Column('allowed_domains', sa.JSON(), nullable=True),
            sa.Column('allowed_ip', sa.String(100), nullable=True),
            sa.Column('vps_signature', sa.String(255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
            sa.Column('status_message', sa.String(255), nullable=True, server_default='Active and Verified'),
            sa.Column('downloads_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('last_verified_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, 'asset_licenses'):
        op.drop_table('asset_licenses')
    if _table_exists(conn, 'modular_assets'):
        op.drop_table('modular_assets')
    if _table_exists(conn, 'agency_company_access'):
        op.drop_table('agency_company_access')
    if _table_exists(conn, 'companies'):
        if _column_exists(conn, 'companies', 'agency_max_companies'):
            op.drop_column('companies', 'agency_max_companies')
        if _column_exists(conn, 'companies', 'max_agents'):
            op.drop_column('companies', 'max_agents')
