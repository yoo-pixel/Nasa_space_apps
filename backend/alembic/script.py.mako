"""$MESSAGE$

Revision ID: $UP$
Revises: $DOWN$
Create Date: $DATE$
"""
from alembic import op
import sqlalchemy as sa
$IMPORTS$

revision = $REPRUP$
down_revision = $REPRDOWN$
branch_labels = $REPRBRANCH$
depends_on = $REPRDEPENDS$

def upgrade() -> None:
    $UPGRADES$

def downgrade() -> None:
    $DOWNGRADES$
