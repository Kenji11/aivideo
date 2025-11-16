"""Add final_music_url column

Revision ID: 001_add_final_music_url
Revises: 
Create Date: 2025-11-16 02:15:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_final_music_url'
down_revision = None  # This is the first migration
branch_labels = None
depends_on = None

def upgrade():
    # Add final_music_url column to video_generations table if it doesn't exist
    # Using IF NOT EXISTS equivalent by checking first
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_generations')]
    
    if 'final_music_url' not in columns:
        op.add_column('video_generations', 
                      sa.Column('final_music_url', sa.String(), nullable=True))

def downgrade():
    # Remove final_music_url column
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_generations')]
    
    if 'final_music_url' in columns:
        op.drop_column('video_generations', 'final_music_url')

