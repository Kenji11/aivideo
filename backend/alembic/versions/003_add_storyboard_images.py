"""Add storyboard_images column

Revision ID: 003_add_storyboard_images
Revises: 002_add_final_music_url
Create Date: 2025-11-16 03:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_storyboard_images'
down_revision = '002_add_final_music_url'
branch_labels = None
depends_on = None

def upgrade():
    # Add storyboard_images column to video_generations table if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_generations')]
    
    if 'storyboard_images' not in columns:
        op.add_column('video_generations', 
                      sa.Column('storyboard_images', sa.JSON(), nullable=True))

def downgrade():
    # Remove storyboard_images column
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_generations')]
    
    if 'storyboard_images' in columns:
        op.drop_column('video_generations', 'storyboard_images')

