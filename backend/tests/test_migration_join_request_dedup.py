"""Tests for the a71e2519b13b migration's duplicate-resolution safety.

These run Alembic directly against a throwaway SQLite file — independent of
the shared app fixtures in conftest.py — so they can set up a "production
database with pre-existing duplicates" scenario precisely, upgrade through
the real migration, and assert on the exact resulting rows.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from config import get_settings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_REVISION = "a36a27fce76f"
TARGET_REVISION = "a71e2519b13b"


@pytest.fixture()
def migration_db():
    tmp_dir = tempfile.mkdtemp(prefix="pov_zen_migration_test_")
    db_path = os.path.join(tmp_dir, "migration_test.db")
    db_url = f"sqlite:///{db_path}"

    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)

    # alembic/env.py deliberately ignores the Config's own sqlalchemy.url and
    # always re-reads get_settings().database_url instead (so a bare `alembic
    # upgrade head` always follows backend/.env). To point it at this test's
    # throwaway file instead of the shared conftest test database, swap the
    # env var + cached Settings for the duration of this fixture only, and
    # restore both afterward so the rest of the suite is unaffected.
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url
    get_settings.cache_clear()
    try:
        # Stop at the parent revision — schema exists, but the partial
        # unique index does not yet, matching a pre-upgrade production DB.
        command.upgrade(cfg, PARENT_REVISION)

        engine = sa.create_engine(db_url)
        yield cfg, engine
        engine.dispose()
    finally:
        if original_database_url is not None:
            os.environ["DATABASE_URL"] = original_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()


def _seed_minimal_group_and_users(conn, *, group_id: str, owner_account: str, user_specs: list[str]) -> None:
    now = datetime.now(timezone.utc)
    conn.execute(
        sa.text(
            "INSERT INTO auth_accounts (id, email, password_hash, account_type, created_at) "
            "VALUES (:id, :email, 'x', 'owner', :now)"
        ),
        {"id": owner_account, "email": f"{owner_account}@example.com", "now": now},
    )
    owner_id = f"OWN-{owner_account}"
    conn.execute(
        sa.text(
            "INSERT INTO owners (owner_id, account_id, name, created_at) VALUES (:oid, :aid, 'Owner', :now)"
        ),
        {"oid": owner_id, "aid": owner_account, "now": now},
    )
    conn.execute(
        sa.text(
            "INSERT INTO pg_groups (group_id, owner_id, pg_name, access_key_hash, created_at) "
            "VALUES (:gid, :oid, 'PG', :hash, :now)"
        ),
        {"gid": group_id, "oid": owner_id, "hash": f"hash-{group_id}", "now": now},
    )
    for user_id in user_specs:
        account_id = f"acct-{user_id}"
        conn.execute(
            sa.text(
                "INSERT INTO auth_accounts (id, email, password_hash, account_type, created_at) "
                "VALUES (:id, :email, 'x', 'user', :now)"
            ),
            {"id": account_id, "email": f"{account_id}@example.com", "now": now},
        )
        conn.execute(
            sa.text(
                "INSERT INTO users (user_id, account_id, name, created_at) VALUES (:uid, :aid, 'User', :now)"
            ),
            {"uid": user_id, "aid": account_id, "now": now},
        )


def _insert_join_request(conn, *, request_id: str, user_id: str, group_id: str, status: str, requested_at: datetime):
    conn.execute(
        sa.text(
            "INSERT INTO join_requests (request_id, user_id, group_id, status, requested_at) "
            "VALUES (:rid, :uid, :gid, :status, :requested_at)"
        ),
        {"rid": request_id, "uid": user_id, "gid": group_id, "status": status, "requested_at": requested_at},
    )


def test_migration_resolves_pre_existing_duplicates_and_creates_index(migration_db):
    cfg, engine = migration_db
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        _seed_minimal_group_and_users(
            conn, group_id="PG-A", owner_account="owner-a", user_specs=["USR-DUP", "USR-SOLO"]
        )
        _seed_minimal_group_and_users(conn, group_id="PG-B", owner_account="owner-b", user_specs=[])
        _seed_minimal_group_and_users(conn, group_id="PG-C", owner_account="owner-c", user_specs=[])

        # USR-DUP has three pending requests (the pre-fix bug scenario) at
        # distinct times — the most recent (req-3) must be the one retained.
        _insert_join_request(
            conn, request_id="req-1", user_id="USR-DUP", group_id="PG-A",
            status="pending", requested_at=now - timedelta(hours=3),
        )
        _insert_join_request(
            conn, request_id="req-2", user_id="USR-DUP", group_id="PG-B",
            status="pending", requested_at=now - timedelta(hours=2),
        )
        _insert_join_request(
            conn, request_id="req-3", user_id="USR-DUP", group_id="PG-C",
            status="pending", requested_at=now - timedelta(hours=1),
        )

        # USR-SOLO has exactly one pending request — must be left untouched.
        _insert_join_request(
            conn, request_id="req-solo", user_id="USR-SOLO", group_id="PG-A",
            status="pending", requested_at=now,
        )

    # This must not raise — the whole point of the fix.
    command.upgrade(cfg, TARGET_REVISION)

    with engine.connect() as conn:
        rows = {
            r[0]: dict(r._mapping)
            for r in conn.execute(
                sa.text("SELECT request_id, status, decided_at FROM join_requests ORDER BY request_id")
            )
        }

        # Deterministic rule: most recent requested_at (req-3) survives as pending.
        assert rows["req-3"]["status"] == "pending"
        assert rows["req-3"]["decided_at"] is None

        # The older duplicates are rejected, not deleted — still present, with decided_at set.
        assert rows["req-1"]["status"] == "rejected"
        assert rows["req-1"]["decided_at"] is not None
        assert rows["req-2"]["status"] == "rejected"
        assert rows["req-2"]["decided_at"] is not None

        # The non-duplicate user's request is completely unaffected.
        assert rows["req-solo"]["status"] == "pending"
        assert rows["req-solo"]["decided_at"] is None

        # Exactly one pending row remains for USR-DUP.
        pending_for_dup = conn.execute(
            sa.text("SELECT COUNT(*) FROM join_requests WHERE user_id = 'USR-DUP' AND status = 'pending'")
        ).scalar()
        assert pending_for_dup == 1

        # The partial unique index now exists and is enforced.
        inspector = sa.inspect(conn)
        index_names = {idx["name"] for idx in inspector.get_indexes("join_requests")}
        assert "uq_one_pending_request_per_user" in index_names

    with engine.begin() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            _insert_join_request(
                conn, request_id="req-should-fail", user_id="USR-SOLO", group_id="PG-B",
                status="pending", requested_at=now,
            )


def test_migration_is_safe_to_reapply(migration_db):
    """Downgrade (drops the index only, per the documented irreversibility
    of the dedup step) then upgrade again must succeed without error."""
    cfg, engine = migration_db
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        _seed_minimal_group_and_users(conn, group_id="PG-A", owner_account="owner-a", user_specs=["USR-DUP"])
        _seed_minimal_group_and_users(conn, group_id="PG-B", owner_account="owner-b", user_specs=[])
        _insert_join_request(
            conn, request_id="req-1", user_id="USR-DUP", group_id="PG-A",
            status="pending", requested_at=now - timedelta(hours=1),
        )
        _insert_join_request(
            conn, request_id="req-2", user_id="USR-DUP", group_id="PG-B",
            status="pending", requested_at=now,
        )

    command.upgrade(cfg, TARGET_REVISION)
    command.downgrade(cfg, PARENT_REVISION)
    command.upgrade(cfg, TARGET_REVISION)  # must not raise the second time

    with engine.connect() as conn:
        inspector = sa.inspect(conn)
        index_names = {idx["name"] for idx in inspector.get_indexes("join_requests")}
        assert "uq_one_pending_request_per_user" in index_names

        pending_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM join_requests WHERE user_id = 'USR-DUP' AND status = 'pending'")
        ).scalar()
        assert pending_count == 1
