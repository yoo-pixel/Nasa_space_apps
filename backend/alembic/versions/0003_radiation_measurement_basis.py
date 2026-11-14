"""Record whether radiation values are interval, cumulative, or rate readings."""
from alembic import op
import sqlalchemy as sa

revision = "0003_radiation_measurement_basis"
down_revision = "0002_personalized_monitoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("radiation_exposure_records")}
    if "measurement_basis" not in columns:
        op.add_column(
            "radiation_exposure_records",
            sa.Column("measurement_basis", sa.String(30), nullable=False, server_default="interval"),
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("radiation_exposure_records")}
    if "measurement_basis" in columns:
        with op.batch_alter_table("radiation_exposure_records") as batch:
            batch.drop_column("measurement_basis")
