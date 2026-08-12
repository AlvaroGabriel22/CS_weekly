"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2026-08-08 00:00:00.000000

This migration creates the complete database schema with all tables,
indexes, and constraints for the QWI (Quality Weekly Intelligence) system.

Tables created:
- users: User accounts and profiles
- writing_profiles: AI writing preferences
- templates: Report templates
- activities: Weekly activities log
- activity_metadata: AI-processed metadata for activities
- attachments: File attachments for activities
- weekly_reports: Generated weekly reports
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables"""

    # Create ENUM types
    op.execute('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))')

    # users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('employee_id', sa.String(50), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('department', sa.String(255), nullable=False, server_default='Qualidade'),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('sector', sa.String(50), nullable=False, server_default='CSI'),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_employee_id', 'users', ['employee_id'])
    op.create_index('ix_users_created_at', 'users', ['created_at'])

    # writing_profiles table
    op.create_table(
        'writing_profiles',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, unique=True),
        sa.Column('default_language', sa.String(10), nullable=False, server_default='pt'),
        sa.Column('default_template_id', sa.String(36), nullable=True),
        sa.Column('writing_tone', sa.String(50), nullable=False, server_default='specialist'),
        sa.Column('objectivity', sa.String(20), nullable=False, server_default='high'),
        sa.Column('technical_level', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('auto_conclusions', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_next_steps', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_impact', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_describe_images', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_explain_charts', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('personal_prompt', sa.Text(), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_writing_profiles_user_id', 'writing_profiles', ['user_id'])

    # templates table
    op.create_table(
        'templates',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('department', sa.String(255), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, server_default='pt'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('slides_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_templates_created_at', 'templates', ['created_at'])

    # activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project', sa.String(255), nullable=True),
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('activity_date', sa.DateTime(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('include_in_weekly', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='registered'),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint('week_number BETWEEN 1 AND 53', name='chk_week_number_range'),
    )
    op.create_index('ix_activities_user_id', 'activities', ['user_id'])
    op.create_index('ix_activities_week_number', 'activities', ['week_number'])
    op.create_index('ix_activities_year', 'activities', ['year'])
    op.create_index('ix_activities_activity_date', 'activities', ['activity_date'])
    op.create_index('ix_activities_status', 'activities', ['status'])
    op.create_index('ix_activities_user_week_year', 'activities', ['user_id', 'year', 'week_number'])

    # activity_metadata table
    op.create_table(
        'activity_metadata',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('activity_id', sa.String(36), nullable=False, unique=True),
        sa.Column('project', sa.String(255), nullable=True),
        sa.Column('supplier', sa.String(255), nullable=True),
        sa.Column('line', sa.String(255), nullable=True),
        sa.Column('process', sa.String(255), nullable=True),
        sa.Column('product', sa.String(255), nullable=True),
        sa.Column('category', sa.String(255), nullable=True),
        sa.Column('activity_type', sa.String(255), nullable=True),
        sa.Column('defect_type', sa.String(255), nullable=True),
        sa.Column('related_kpis', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('keywords', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('technical_summary', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_activity_metadata_activity_id', 'activity_metadata', ['activity_id'])

    # attachments table
    op.create_table(
        'attachments',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('activity_id', sa.String(36), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('image_usage', sa.String(50), nullable=True),
        sa.Column('include_in_weekly', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('manual_caption', sa.Text(), nullable=True),
        sa.Column('ai_caption', sa.Text(), nullable=True),
        sa.Column('ai_analysis', sa.JSON(), nullable=True),
        sa.Column('kpi_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_attachments_activity_id', 'attachments', ['activity_id'])
    op.create_index('ix_attachments_file_type', 'attachments', ['file_type'])
    op.create_index('ix_attachments_created_at', 'attachments', ['created_at'])

    # weekly_reports table
    op.create_table(
        'weekly_reports',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('template_id', sa.String(36), nullable=True),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('language', sa.String(10), nullable=False, server_default='pt'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('pptx_path', sa.String(500), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('coverage', sa.JSON(), nullable=True),
        sa.Column('confidence_index', sa.JSON(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='SET NULL'),
        sa.CheckConstraint('week_number BETWEEN 1 AND 53', name='chk_weekly_week_range'),
        sa.UniqueConstraint('user_id', 'year', 'week_number', name='uq_user_year_week'),
    )
    op.create_index('ix_weekly_reports_user_id', 'weekly_reports', ['user_id'])
    op.create_index('ix_weekly_reports_week_number', 'weekly_reports', ['week_number'])
    op.create_index('ix_weekly_reports_status', 'weekly_reports', ['status'])
    op.create_index('ix_weekly_reports_user_year_week', 'weekly_reports', ['user_id', 'year', 'week_number'])

    # Add foreign key for writing_profiles.default_template_id
    op.create_foreign_key(
        'fk_writing_profiles_template',
        'writing_profiles',
        'templates',
        ['default_template_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('weekly_reports')
    op.drop_table('attachments')
    op.drop_table('activity_metadata')
    op.drop_table('activities')
    op.drop_table('templates')
    op.drop_table('writing_profiles')
    op.drop_table('users')
