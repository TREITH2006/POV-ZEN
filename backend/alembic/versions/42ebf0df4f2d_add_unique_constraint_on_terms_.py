"""add unique constraint on terms_acceptance account_id version

Revision ID: 42ebf0df4f2d
Revises: a71e2519b13b
Create Date: 2026-09-03 19:41:54.315448

Safety note: nothing previously prevented an account from accepting the same
Terms version more than once, so an existing production database may already
contain duplicate (account_id, version) rows. Before adding the unique
constraint, this migration deterministically resolves any duplicates:

  Rule: for each (account_id, version) pair, the row with the earliest
  accepted_at is retained (ties broken by id, ascending) — the earliest
  acceptance is the historically accurate "when did they first agree"
  record. The later duplicate rows are deleted, not preserved under a
  different status: unlike a join request, a duplicate acceptance record
  carries no separate downstream state or consequence — it is purely a
  redundant re-statement of the same already-recorded fact, so removing the
  redundant rows discards nothing of informational value.

Both steps are safe to run more than once: the dedup DELETE naturally
becomes a no-op once no duplicates remain, and the constraint is only
created if it doesn't already exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42ebf0df4f2d'
down_revision: Union[str, None] = 'a71e2519b13b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = 'uq_account_version_acceptance'


def _dedupe_terms_acceptance(bind) -> None:
    bind.execute(
        sa.text(
            """
            DELETE FROM terms_acceptance
            WHERE id IN (
                SELECT id FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY account_id, version
                            ORDER BY accepted_at ASC, id ASC
                        ) AS rn
                    FROM terms_acceptance
                ) ranked
                WHERE rn > 1
            )
            """
        )
    )


def _constraint_exists(bind) -> bool:
    inspector = sa.inspect(bind)
    names = {c["name"] for c in inspector.get_unique_constraints("terms_acceptance")}
    return _CONSTRAINT_NAME in names


def upgrade() -> None:
    bind = op.get_bind()

    _dedupe_terms_acceptance(bind)

    if not _constraint_exists(bind):
        with op.batch_alter_table("terms_acceptance") as batch_op:
            batch_op.create_unique_constraint(_CONSTRAINT_NAME, ["account_id", "version"])


def downgrade() -> None:
    bind = op.get_bind()
    if _constraint_exists(bind):
        with op.batch_alter_table("terms_acceptance") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")
