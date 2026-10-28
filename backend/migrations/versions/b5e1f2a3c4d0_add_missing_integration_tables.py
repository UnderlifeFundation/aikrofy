"""add missing integration tables and extend erpplatform enum

Revision ID: b5e1f2a3c4d0
Revises: 4dd1f904a7a4
Create Date: 2026-07-30 15:35:00.000000

Adds:
  - crm_configs table (CRMConfig model) - idempotent, skips if exists
  - ecommerce_configs table (EcommerceConfig model) - idempotent, skips if exists
  - payment_gateway_configs table (PaymentGatewayConfig model) - idempotent, skips if exists
  - payment_transactions table (PaymentTransaction model) - idempotent, skips if exists
  - Extends erpplatform enum with CONTIFICO, MYSQL values (MySQL ALTER TABLE)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = 'b5e1f2a3c4d0'
down_revision = '4dd1f904a7a4'
branch_labels = None
depends_on = None


def _table_exists(conn, table_name):
    """Check if a table exists in the current DB."""
    inspector = sa_inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    # ------------------------------------------------------------------ #
    # 1. Extend the erpplatform ENUM in MySQL
    # ------------------------------------------------------------------ #
    if dialect == 'mysql':
        # MySQL: check current ENUM values and only ALTER if needed
        result = conn.execute(sa.text(
            "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'erp_configs' AND COLUMN_NAME = 'platform'"
        ))
        row = result.fetchone()
        if row:
            current_enum = row[0]
            needs_contifico = 'CONTIFICO' not in current_enum
            needs_mysql = "'mysql'" not in current_enum.lower() or 'MYSQL' not in current_enum
            if needs_contifico or needs_mysql:
                op.execute(sa.text(
                    "ALTER TABLE erp_configs MODIFY COLUMN platform "
                    "ENUM('SAP_B1','NETSUITE','ODOO','DYNAMICS_BC','CONTIFICO','MYSQL','CUSTOM') NOT NULL"
                ))

    # ------------------------------------------------------------------ #
    # 2. crm_configs table (idempotent)
    # ------------------------------------------------------------------ #
    if not _table_exists(conn, 'crm_configs'):
        op.create_table(
            'crm_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column(
                'platform',
                sa.Enum('hubspot', 'salesforce', 'pipedrive', 'zoho', 'dynamics_365', 'custom',
                        name='crmplatform'),
                nullable=False
            ),
            sa.Column('crm_url', sa.String(length=512), nullable=True),
            sa.Column('credentials', sa.JSON(), nullable=True),
            sa.Column('custom_schema', sa.JSON(), nullable=True),
            sa.Column('is_connected', sa.Boolean(), nullable=True, default=False),
            sa.Column('last_tested_at', sa.DateTime(), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_id'),
        )

    # ------------------------------------------------------------------ #
    # 3. ecommerce_configs table (idempotent)
    # ------------------------------------------------------------------ #
    if not _table_exists(conn, 'ecommerce_configs'):
        op.create_table(
            'ecommerce_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column(
                'platform',
                sa.Enum('shopify', 'woocommerce', 'vtex', 'magento', 'prestashop', 'bigcommerce',
                        name='ecommerceplatform'),
                nullable=False
            ),
            sa.Column('store_url', sa.String(length=512), nullable=False),
            sa.Column('credentials', sa.JSON(), nullable=True),
            sa.Column('is_connected', sa.Boolean(), nullable=True, default=False),
            sa.Column('last_tested_at', sa.DateTime(), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_id'),
        )

    # ------------------------------------------------------------------ #
    # 4. payment_gateway_configs table (idempotent)
    # ------------------------------------------------------------------ #
    if not _table_exists(conn, 'payment_gateway_configs'):
        op.create_table(
            'payment_gateway_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column(
                'gateway_provider',
                sa.Enum('stripe', 'paypal', 'mercadopago', 'kushki', 'nuvei',
                        'dlocal_go', 'authorize_net', 'custom',
                        name='gatewayprovider'),
                nullable=False
            ),
            sa.Column('display_name', sa.String(length=100), nullable=True),
            sa.Column('api_endpoint', sa.String(length=512), nullable=True),
            sa.Column('credentials', sa.JSON(), nullable=True),
            sa.Column('config_payload', sa.JSON(), nullable=True),
            sa.Column('sandbox_mode', sa.Boolean(), nullable=True, default=True),
            sa.Column('is_connected', sa.Boolean(), nullable=True, default=False),
            sa.Column('last_tested_at', sa.DateTime(), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('company_id'),
        )

    # ------------------------------------------------------------------ #
    # 5. payment_transactions table (idempotent)
    # ------------------------------------------------------------------ #
    if not _table_exists(conn, 'payment_transactions'):
        op.create_table(
            'payment_transactions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('gateway_config_id', sa.Integer(), nullable=True),
            sa.Column('customer_email', sa.String(length=255), nullable=True),
            sa.Column('customer_phone', sa.String(length=50), nullable=True),
            sa.Column('customer_name', sa.String(length=255), nullable=True),
            sa.Column('amount', sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column(
                'status',
                sa.Enum('pending', 'authorized', 'captured', 'failed', 'refunded', 'voided',
                        name='transactionstatus'),
                nullable=False,
                server_default='pending'
            ),
            sa.Column('external_transaction_id', sa.String(length=255), nullable=True),
            sa.Column('idempotency_key', sa.String(length=255), nullable=False),
            sa.Column('payment_url', sa.Text(), nullable=True),
            sa.Column(
                'channel',
                sa.Enum('whatsapp', 'telegram', 'webchat', 'voice', 'dashboard',
                        name='transactionchannel'),
                nullable=True
            ),
            sa.Column('agent_id', sa.Integer(), nullable=True),
            sa.Column('conversation_id', sa.Integer(), nullable=True),
            sa.Column('error_code', sa.String(length=100), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('gateway_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
            sa.ForeignKeyConstraint(['gateway_config_id'], ['payment_gateway_configs.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('idempotency_key'),
        )


def downgrade():
    # Only drop tables that we track via this migration
    conn = op.get_bind()
    if _table_exists(conn, 'payment_transactions'):
        op.drop_table('payment_transactions')
    if _table_exists(conn, 'payment_gateway_configs'):
        op.drop_table('payment_gateway_configs')
    if _table_exists(conn, 'ecommerce_configs'):
        op.drop_table('ecommerce_configs')
    if _table_exists(conn, 'crm_configs'):
        op.drop_table('crm_configs')
    # Note: MySQL ENUM downgrade requires manual intervention.
