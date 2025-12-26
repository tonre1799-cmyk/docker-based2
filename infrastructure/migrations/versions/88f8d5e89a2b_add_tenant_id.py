"""add tenant_id to all tables

Revision ID: 88f8d5e89a2b
Revises: 
Create Date: 2025-12-25 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '88f8d5e89a2b'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # List of tables to add tenant_id to
    tables = [
        'analytics',
        'heatmaps',
        'tracking_events',
        'person_detections',
        'processed_files'
    ]
    
    for table in tables:
        # Add column if it doesn't exist
        op.add_column(table, sa.Column('tenant_id', sa.String(), nullable=False, server_default='default'))
        # Add index for performance
        op.create_index(f'idx_{table}_tenant', table, ['tenant_id'])

def downgrade():
    tables = [
        'analytics',
        'heatmaps',
        'tracking_events',
        'person_detections',
        'processed_files'
    ]
    
    for table in tables:
        op.drop_index(f'idx_{table}_tenant', table_name=table)
        op.drop_column(table, 'tenant_id')
