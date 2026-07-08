"""Add base_url to tenant_llm_settings (for self-hosted providers like Ollama)

Revision ID: 005
Revises: 004
Create Date: 2026-07-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenant_llm_settings', sa.Column('base_url', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('tenant_llm_settings', 'base_url')
