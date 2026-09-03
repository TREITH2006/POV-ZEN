"""add unique constraint on food_feedback menu_id user_id

Revision ID: b073e4d3498a
Revises: 42ebf0df4f2d
Create Date: 2026-09-03 19:52:07.000000

Safety note: nothing previously prevented a resident from submitting
multiple feedback rows for the same menu, so an existing production
database may already contain duplicates. Before adding the unique
constraint, this migration deterministically resolves any duplicates:

  Rule: for each (menu_id, user_id) pair, the row with the most recent
  created_at is retained (ties broken by id, descending) — a resident's
  latest stated opinion is the one that matters going forward, unlike
  Terms acceptance where the earliest record is the historically accurate
  one. The older duplicate rows are deleted: food feedback carries no
  separate downstream state or approval workflow, so an older duplicate
  is purely redundant once a newer one from the same resident exists.

Also adds the `updated_at` column that upsert-style feedback submissions
now rely on, backfilling it from created_at for existing rows.

Both the dedup step and the constraint creation are safe to run more than
once: the dedup DELETE naturally becomes a no-op once no duplicates remain,
and the constraint is only created if it doesn't already exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b073e4d3498a'
down_revision: Union[str, None] = '42ebf0df4f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = 'uq_menu_user_feedback'


def _dedupe_food_feedback(bind) -> None:
    bind.execute(
        sa.text(
            """
            DELETE FROM food_feedback
            WHERE id IN (
                SELECT id FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY menu_id, user_id
                            ORDER BY created_at DESC, id DESC
                        ) AS rn
                    FROM food_feedback
                ) ranked
                WHERE rn > 1
            )
            """
        )
    )


def _constraint_exists(bind) -> bool:
    inspector = sa.inspect(bind)
    names = {c["name"] for c in inspector.get_unique_constraints("food_feedback")}
    return _CONSTRAINT_NAME in names


def _column_exists(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _column_exists(bind, "food_feedback", "updated_at"):
        with op.batch_alter_table("food_feedback") as batch_op:
            batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        bind.execute(sa.text("UPDATE food_feedback SET updated_at = created_at WHERE updated_at IS NULL"))
        with op.batch_alter_table("food_feedback") as batch_op:
            batch_op.alter_column("updated_at", nullable=False)

    _dedupe_food_feedback(bind)

    if not _constraint_exists(bind):
        with op.batch_alter_table("food_feedback") as batch_op:
            batch_op.create_unique_constraint(_CONSTRAINT_NAME, ["menu_id", "user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _constraint_exists(bind):
        with op.batch_alter_table("food_feedback") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")
    if _column_exists(bind, "food_feedback", "updated_at"):
        with op.batch_alter_table("food_feedback") as batch_op:
            batch_op.drop_column("updated_at")
