"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-12-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), default='user'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('device_id', sa.String(100), primary_key=True, index=True),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('owner_address', sa.String(42), nullable=True),
        sa.Column('status', sa.String(20), default='PENDING'),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('hashed_signature', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create network_usage table
    op.create_table(
        'network_usage',
        sa.Column('usage_id', sa.String(100), primary_key=True, index=True),
        sa.Column('device_id', sa.String(100), sa.ForeignKey('devices.device_id', ondelete='CASCADE'), index=True),
        sa.Column('bytes_transmitted', sa.BigInteger(), nullable=False, default=0),
        sa.Column('bytes_received', sa.BigInteger(), default=0),
        sa.Column('connection_quality', sa.Integer(), default=100),
        sa.Column('user_sessions', sa.Integer(), default=0),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('compensated', sa.Boolean(), default=False),
    )
    
    # Create compensation_transactions table
    op.create_table(
        'compensation_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.String(100), sa.ForeignKey('devices.device_id', ondelete='CASCADE'), index=True),
        sa.Column('owner_address', sa.String(42), index=True),
        sa.Column('usage_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('average_quality', sa.Float(), nullable=True),
        sa.Column('reward_amount', sa.Float(), nullable=True),
        sa.Column('blockchain_tx_hash', sa.String(66), unique=True, nullable=True),
        sa.Column('status', sa.String(20), default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
    
    # Create indexes
    op.create_index('idx_devices_status', 'devices', ['status'])
    op.create_index('idx_network_usage_timestamp', 'network_usage', ['timestamp'])
    op.create_index('idx_compensation_owner', 'compensation_transactions', ['owner_address'])


def downgrade() -> None:
    op.drop_table('compensation_transactions')
    op.drop_table('network_usage')
    op.drop_table('devices')
    op.drop_table('users')
