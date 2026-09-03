"""add partial unique index for one pending join request per user

Revision ID: a71e2519b13b
Revises: a36a27fce76f
Create Date: 2026-09-03 16:54:13.754211

Safety note: an existing production database may already contain duplicate
pending join_requests for the same user (across different PG groups) from
before the application-level guard against this existed. Creating the
partial unique index directly against such data would fail outright. Before
creating the index, this migration deterministically resolves any existing
duplicates:

  Rule: for each user with more than one pending join_request, the row with
  the most recent requested_at is retained as pending (ties broken by
  request_id, descending, for full determinism). Every other pending row for
  that user is marked status='rejected' rather than deleted — no historical
  data is discarded, and status='rejected' correctly reflects that the row
  no longer represents an actionable pending request. decided_at is set to
  the migration's run time; this is a system data-hygiene action, not a real
  Owner decision, but the existing code assumes decided_at is always set
  once a request leaves 'pending', so this preserves that invariant instead
  of introducing a new state.

Both the dedup step and the index creation are written to be safe to run
more than once: the dedup UPDATE naturally becomes a no-op once no
duplicates remain, and the index is only created if it doesn't already
exist.
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a71e2519b13b'
down_revision: Union[str, None] = 'a36a27fce76f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = 'uq_one_pending_request_per_user'


def _resolve_duplicate_pending_requests(bind) -> None:
    """Keep the most-recently-requested pending row per user; reject the
    rest. Idempotent: once no user has more than one pending row, this
    UPDATE matches zero rows."""
    bind.execute(
        sa.text(
            """
            UPDATE join_requests
            SET status = 'rejected', decided_at = :now
            WHERE request_id IN (
                SELECT request_id FROM (
                    SELECT
                        request_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id
                            ORDER BY requested_at DESC, request_id DESC
                        ) AS rn
                    FROM join_requests
                    WHERE status = 'pending'
                ) ranked
                WHERE rn > 1
            )
            """
        ),
        {"now": datetime.now(timezone.utc)},
    )


def _index_exists(bind) -> bool:
    inspector = sa.inspect(bind)
    return any(idx["name"] == _INDEX_NAME for idx in inspector.get_indexes("join_requests"))


def upgrade() -> None:
    bind = op.get_bind()

    _resolve_duplicate_pending_requests(bind)

    if not _index_exists(bind):
        op.create_index(
            _INDEX_NAME,
            'join_requests',
            ['user_id'],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        )


def downgrade() -> None:
    # The duplicate-resolution step is intentionally NOT reversed: there is
    # no sound way to know which historical rows were auto-rejected by this
    # migration versus genuinely rejected by an Owner, so downgrading only
    # removes the index, not the data changes.
    bind = op.get_bind()
    if _index_exists(bind):
        op.drop_index(
            _INDEX_NAME,
            table_name='join_requests',
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        )
