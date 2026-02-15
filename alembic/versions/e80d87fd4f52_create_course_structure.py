"""create_course_structure

Revision ID: e80d87fd4f52
Revises: b50a670c4ebd
Create Date: 2026-02-15 14:18:38.083062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e80d87fd4f52'
down_revision: Union[str, Sequence[str], None] = 'b50a670c4ebd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_image', sa.String(length=255), nullable=True),
        sa.Column('level', sa.String(length=50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)

    # 2. Create units table
    op.create_table(
        'units',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_units_id'), 'units', ['id'], unique=False)
    op.create_index(op.f('ix_units_course_id'), 'units', ['course_id'], unique=False)

    # 3. Create lessons table
    # Note: lesson is the core entity that links to a video
    op.create_table(
        'lessons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
        sa.Column('video_id', sa.Integer(), nullable=True), # Link to existing videos table
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False), # Soft delete
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        # New fields for Journal-Based Workflow tracking
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='PENDING'), # PENDING, PROCESSING, READY, FAILED
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
        # Assuming 'videos' table exists. If video is deleted, set this to null (or we handle it via soft delete logic)
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lessons_id'), 'lessons', ['id'], unique=False)
    op.create_index(op.f('ix_lessons_unit_id'), 'lessons', ['unit_id'], unique=False)

    # 4. Create task_journals table (FOR RECOVERY & LOGGING)
    op.create_table(
        'task_journals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(length=50), nullable=False), # e.g., TRANSCODE, SUBTITLE, TRANSLATE
        sa.Column('action', sa.String(length=20), nullable=False), # START, COMPLETE, FAIL
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True), # Input params, file paths
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_journals_lesson_id'), 'task_journals', ['lesson_id'], unique=False)
    # Compound index for efficient querying of last status per step
    op.create_index('ix_task_journals_lesson_step', 'task_journals', ['lesson_id', 'step_name'], unique=False)

    # 5. Create user_progress table
    op.create_table(
        'user_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False), # Assuming users table exists or will exist
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='LOCKED'), # LOCKED, ACTIVE, COMPLETED, SKIPPED
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_position_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson_progress')
    )
    op.create_index(op.f('ix_user_progress_user_id'), 'user_progress', ['user_id'], unique=False)
    
    # 6. Create practice_submissions table
    op.create_table(
        'practice_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('practice_type', sa.String(length=50), nullable=False), # SHADOWING, LISTENING
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('content_url', sa.String(length=255), nullable=True), # Audio/Text file
        sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True), # AI feedback
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('practice_submissions')
    op.drop_table('user_progress')
    op.drop_table('task_journals')
    op.drop_table('lessons')
    op.drop_table('units')
    op.drop_table('courses')
