"""initial schema with video_generations and assets tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-11-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create assets table
    op.create_table('assets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('s3_key', sa.String(), nullable=False),
        sa.Column('s3_url', sa.String(), nullable=True),
        sa.Column('asset_type', sa.Enum('IMAGE', 'VIDEO', 'AUDIO', name='assettype'), nullable=False),
        sa.Column('source', sa.Enum('USER_UPLOAD', 'SYSTEM_GENERATED', name='assetsource'), nullable=False),
        sa.Column('file_name', sa.String(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('asset_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create video_generations table
    op.create_table('video_generations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('prompt', sa.String(), nullable=False),
        sa.Column('prompt_validated', sa.String(), nullable=True),
        sa.Column('reference_assets', sa.JSON(), nullable=True),
        sa.Column('spec', sa.JSON(), nullable=True),
        sa.Column('template', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'VALIDATING', 'GENERATING_ANIMATIC', 'GENERATING_REFERENCES', 'GENERATING_CHUNKS', 'REFINING', 'EXPORTING', 'COMPLETE', 'FAILED', name='videostatus'), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('current_phase', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('animatic_urls', sa.JSON(), nullable=True),
        sa.Column('chunk_urls', sa.JSON(), nullable=True),
        sa.Column('stitched_url', sa.String(), nullable=True),
        sa.Column('refined_url', sa.String(), nullable=True),
        sa.Column('final_video_url', sa.String(), nullable=True),
        sa.Column('final_music_url', sa.String(), nullable=True),
        sa.Column('phase_outputs', sa.JSON(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('cost_breakdown', sa.JSON(), nullable=True),
        sa.Column('generation_time_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('video_generations')
    op.drop_table('assets')
    op.execute('DROP TYPE IF EXISTS videostatus')
    op.execute('DROP TYPE IF EXISTS assettype')
    op.execute('DROP TYPE IF EXISTS assetsource')

