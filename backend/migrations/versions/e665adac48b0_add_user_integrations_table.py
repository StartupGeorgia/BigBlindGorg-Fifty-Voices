"""add user_integrations table

Revision ID: e665adac48b0
Revises: 91acf3ffe096
Create Date: 2025-11-28 03:52:03.966199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e665adac48b0'
down_revision: Union[str, Sequence[str], None] = '91acf3ffe096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Table already exists from migration a7176cbf6e3a, just add workspace_id column if missing
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='user_integrations' AND column_name='workspace_id'")
    )
    if result.fetchone() is None:
        op.add_column('user_integrations', sa.Column('workspace_id', sa.Uuid(), nullable=True))
        op.create_foreign_key('fk_user_integrations_workspace', 'user_integrations', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')
        op.create_index(op.f('ix_user_integrations_workspace_id'), 'user_integrations', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Only drop the workspace_id column we added
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='user_integrations' AND column_name='workspace_id'")
    )
    if result.fetchone() is not None:
        op.drop_index(op.f('ix_user_integrations_workspace_id'), table_name='user_integrations')
        op.drop_constraint('fk_user_integrations_workspace', 'user_integrations', type_='foreignkey')
        op.drop_column('user_integrations', 'workspace_id')
