"""add landing pages tables

Revision ID: aa89d849cb15
Revises: a9f4e2b1c3d8
Create Date: 2026-07-11 03:41:55.291536

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa89d849cb15'
down_revision = 'a9f4e2b1c3d8'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing tables to prevent "Table already exists" errors during manual/recovery runs
    op.execute("DROP TABLE IF EXISTS landing_page_custom_domains;")
    op.execute("DROP TABLE IF EXISTS landing_page_elements;")
    op.execute("DROP TABLE IF EXISTS landing_page_visits;")
    op.execute("DROP TABLE IF EXISTS landing_page_versions;")
    op.execute("DROP TABLE IF EXISTS landing_pages;")

    # 1. landing_pages
    op.create_table(
        'landing_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('css_content', sa.Text(), nullable=True),
        sa.Column('js_content', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='landingpagestatus'), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('is_primary', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('custom_domain', sa.String(length=255), nullable=True),
        sa.Column('custom_domain_verified', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('token_cost', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('meta_title', sa.String(length=255), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('og_image_url', sa.String(length=500), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('conversions_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('llm_model', sa.String(length=100), nullable=True, server_default='gpt-5-nano'),
        sa.Column('generation_prompt', sa.Text(), nullable=True),
        sa.Column('screenshot_url', sa.String(length=500), nullable=True),
        sa.Column('generation_status', sa.String(length=50), nullable=True, server_default='idle'),
        sa.Column('generation_error', sa.Text(), nullable=True),
        sa.Column('llm_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'slug', name='uq_landing_company_slug')
    )

    # 2. landing_page_versions
    op.create_table(
        'landing_page_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('landing_page_id', sa.Integer(), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('css_content', sa.Text(), nullable=True),
        sa.Column('js_content', sa.Text(), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('change_summary', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['landing_page_id'], ['landing_pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. landing_page_visits
    op.create_table(
        'landing_page_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('landing_page_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('visitor_ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('utm_source', sa.String(length=255), nullable=True),
        sa.Column('utm_medium', sa.String(length=255), nullable=True),
        sa.Column('utm_campaign', sa.String(length=255), nullable=True),
        sa.Column('utm_term', sa.String(length=255), nullable=True),
        sa.Column('utm_content', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('time_on_page', sa.Integer(), nullable=True),
        sa.Column('scroll_depth', sa.Integer(), nullable=True),
        sa.Column('cta_clicks', sa.JSON(), nullable=True),
        sa.Column('form_submissions', sa.JSON(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('whatsapp_lead_id', sa.String(length=100), nullable=True),
        sa.Column('w_lead_token', sa.String(length=100), nullable=True),
        sa.Column('lead_score_delta', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['landing_page_id'], ['landing_pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_landing_page_visits_session_id'), 'landing_page_visits', ['session_id'], unique=False)

    # 4. landing_page_elements
    op.create_table(
        'landing_page_elements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('landing_page_id', sa.Integer(), nullable=False),
        sa.Column('element_type', sa.String(length=50), nullable=False),
        sa.Column('element_key', sa.String(length=100), nullable=False),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('css_overrides', sa.JSON(), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['landing_page_id'], ['landing_pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. landing_page_custom_domains
    op.create_table(
        'landing_page_custom_domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('landing_page_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('dns_token', sa.String(length=100), nullable=False),
        sa.Column('ssl_status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['landing_page_id'], ['landing_pages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain')
    )


def downgrade():
    op.drop_table('landing_page_custom_domains')
    op.drop_table('landing_page_elements')
    op.drop_index(op.f('ix_landing_page_visits_session_id'), table_name='landing_page_visits')
    op.drop_table('landing_page_visits')
    op.drop_table('landing_page_versions')
    op.drop_table('landing_pages')
