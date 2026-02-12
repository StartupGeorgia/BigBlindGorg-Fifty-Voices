"""Add InXPhone (MOR/Kolmisoft) settings columns to user_settings

Revision ID: 015_add_inxphone_settings
Revises: 2aeb78a98185
Create Date: 2026-02-10

Adds 5 columns for InXPhone/MOR telephony provider configuration:
- inxphone_username: MOR API username
- inxphone_api_key: API secret key for hash computation
- inxphone_device_id: MOR SIP device ID
- inxphone_server_url: MOR billing API base URL
- inxphone_ai_number: AI agent phone number (DID)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "015_add_inxphone_settings"
down_revision: Union[str, Sequence[str], None] = "2aeb78a98185"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add InXPhone settings columns."""
    op.add_column(
        "user_settings",
        sa.Column("inxphone_username", sa.String(255), nullable=True, comment="MOR API username"),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "inxphone_api_key",
            sa.Text,
            nullable=True,
            comment="MOR API secret key for hash computation",
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column("inxphone_device_id", sa.String(255), nullable=True, comment="MOR SIP device ID"),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "inxphone_server_url", sa.Text, nullable=True, comment="MOR billing API base URL"
        ),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "inxphone_ai_number",
            sa.String(50),
            nullable=True,
            comment="InXPhone AI agent phone number (DID)",
        ),
    )


def downgrade() -> None:
    """Remove InXPhone settings columns."""
    op.drop_column("user_settings", "inxphone_ai_number")
    op.drop_column("user_settings", "inxphone_server_url")
    op.drop_column("user_settings", "inxphone_device_id")
    op.drop_column("user_settings", "inxphone_api_key")
    op.drop_column("user_settings", "inxphone_username")
