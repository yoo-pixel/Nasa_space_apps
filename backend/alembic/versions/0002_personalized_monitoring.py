"""Add verified history, personalized learning, bone and radiation records."""
from alembic import op
import sqlalchemy as sa

revision = "0002_personalized_monitoring"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    history_columns = {column["name"] for column in sa.inspect(bind).get_columns("medical_history")}
    additions = [
        sa.Column("source", sa.String(160), nullable=False, server_default="manual"),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="unverified"),
        sa.Column("review_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for column in additions:
        if column.name not in history_columns:
            op.add_column("medical_history", column)

    if "learning_sessions" not in sa.inspect(bind).get_table_names():
        op.create_table(
        "learning_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("astronaut_id", sa.Uuid(), sa.ForeignKey("astronauts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_by", sa.String(120), nullable=False),
        )
        op.create_index("ix_learning_astronaut_started", "learning_sessions", ["astronaut_id", "started_at"])
        op.create_index("ix_learning_sessions_astronaut_id", "learning_sessions", ["astronaut_id"])

    if "personalized_profiles" not in sa.inspect(bind).get_table_names():
        op.create_table(
        "personalized_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("astronaut_id", sa.Uuid(), sa.ForeignKey("astronauts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("approved_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_personalized_profiles_session_id", "personalized_profiles", ["session_id"])
        op.create_index("ix_personalized_profiles_astronaut_id", "personalized_profiles", ["astronaut_id"])

    if "bone_health_assessments" not in sa.inspect(bind).get_table_names():
        op.create_table(
        "bone_health_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("astronaut_id", sa.Uuid(), sa.ForeignKey("astronauts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_type", sa.String(40), nullable=False),
        sa.Column("metric", sa.String(80), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(160), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        )
        op.create_index("ix_bone_astronaut_recorded", "bone_health_assessments", ["astronaut_id", "recorded_at"])
        op.create_index("ix_bone_health_assessments_astronaut_id", "bone_health_assessments", ["astronaut_id"])

    if "radiation_exposure_records" not in sa.inspect(bind).get_table_names():
        op.create_table(
        "radiation_exposure_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("astronaut_id", sa.Uuid(), sa.ForeignKey("astronauts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dosimeter_id", sa.String(100), nullable=False),
        sa.Column("exposure_type", sa.String(30), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(160), nullable=False),
        sa.Column("mission_phase", sa.String(100), nullable=False),
        sa.Column("event", sa.String(160), nullable=False),
        sa.Column("shielding", sa.String(160), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        )
        op.create_index("ix_radiation_astronaut_measured", "radiation_exposure_records", ["astronaut_id", "measured_at"])
        op.create_index("ix_radiation_exposure_records_astronaut_id", "radiation_exposure_records", ["astronaut_id"])


def downgrade() -> None:
    op.drop_table("radiation_exposure_records")
    op.drop_table("bone_health_assessments")
    op.drop_table("personalized_profiles")
    op.drop_table("learning_sessions")
    with op.batch_alter_table("medical_history") as batch:
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by")
        batch.drop_column("review_notes")
        batch.drop_column("verification_status")
        batch.drop_column("source")
