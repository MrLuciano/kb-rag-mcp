"""Tests for Phase 52: Schedule CRUD in MetadataStore."""

import uuid
import tempfile
from pathlib import Path

import pytest

from ingest.core.metadata import MetadataStore


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def store(temp_db):
    store = MetadataStore(db_path=temp_db)
    store.connect()
    yield store
    store.close()


def make_schedule_id() -> str:
    return str(uuid.uuid4())


class TestScheduleCRUD:
    def test_add_schedule(self, store):
        sid = make_schedule_id()
        result = store.add_schedule(
            schedule_id=sid,
            name="weekly-docs",
            cron_expr="0 3 * * 1",
            docs_path="/data/docs",
            product="AppServer",
            workers=4,
            priority="high",
            clean=True,
            force=False,
        )
        assert result["id"] == sid
        assert result["name"] == "weekly-docs"
        assert result["cron_expr"] == "0 3 * * 1"
        assert result["docs_path"] == "/data/docs"
        assert result["product"] == "AppServer"
        assert result["workers"] == 4
        assert result["priority"] == "high"
        assert result["clean"] == 1
        assert result["force"] == 0
        assert result["enabled"] == 1
        assert result["created_at"] > 0
        assert result["updated_at"] == result["created_at"]
        assert result["last_run_at"] is None
        assert result["last_run_status"] is None
        assert result["next_run_at"] is None

    def test_add_schedule_defaults(self, store):
        result = store.add_schedule(
            schedule_id=make_schedule_id(),
            name="defaults-test",
            cron_expr="* * * * *",
            docs_path="/data",
        )
        assert result["workers"] == 2
        assert result["priority"] == "normal"
        assert result["clean"] == 0
        assert result["force"] == 0

    def test_list_schedules_empty(self, store):
        schedules = store.list_schedules()
        assert schedules == []

    def test_list_schedules_order(self, store):
        s1 = store.add_schedule(
            schedule_id=make_schedule_id(),
            name="first", cron_expr="0 3 * * *", docs_path="/a",
        )
        import time
        time.sleep(0.01)
        s2 = store.add_schedule(
            schedule_id=make_schedule_id(),
            name="second", cron_expr="0 4 * * *", docs_path="/b",
        )
        schedules = store.list_schedules()
        assert len(schedules) == 2
        assert schedules[0]["name"] == "second"
        assert schedules[1]["name"] == "first"

    def test_get_schedule(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="get-test",
            cron_expr="*/15 * * * *", docs_path="/tmp",
        )
        result = store.get_schedule(sid)
        assert result is not None
        assert result["name"] == "get-test"

    def test_get_schedule_not_found(self, store):
        result = store.get_schedule("nonexistent-id")
        assert result is None

    def test_update_schedule_all_fields(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="before",
            cron_expr="0 3 * * *", docs_path="/old",
        )
        updated = store.update_schedule(
            schedule_id=sid,
            name="after",
            cron_expr="0 4 * * 1",
            docs_path="/new",
            product="NewProduct",
            workers=8,
            priority="low",
            clean=True,
            force=True,
            enabled=False,
        )
        assert updated["name"] == "after"
        assert updated["cron_expr"] == "0 4 * * 1"
        assert updated["docs_path"] == "/new"
        assert updated["product"] == "NewProduct"
        assert updated["workers"] == 8
        assert updated["priority"] == "low"
        assert updated["clean"] == 1
        assert updated["force"] == 1
        assert updated["enabled"] == 0
        assert updated["updated_at"] > updated["created_at"]

    def test_update_schedule_partial(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="partial",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        updated = store.update_schedule(
            schedule_id=sid, name="renamed",
        )
        assert updated["name"] == "renamed"
        assert updated["cron_expr"] == "0 3 * * *"
        assert updated["docs_path"] == "/data"

    def test_update_schedule_not_found(self, store):
        result = store.update_schedule(
            schedule_id="nonexistent",
            name="anything",
        )
        assert result is None

    def test_delete_schedule(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="to-delete",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        assert store.get_schedule(sid) is not None
        deleted = store.delete_schedule(sid)
        assert deleted is True
        assert store.get_schedule(sid) is None

    def test_delete_schedule_not_found(self, store):
        result = store.delete_schedule("nonexistent")
        assert result is False

    def test_duplicate_name_raises(self, store):
        store.add_schedule(
            schedule_id=make_schedule_id(), name="unique",
            cron_expr="0 3 * * *", docs_path="/a",
        )
        with pytest.raises(Exception):
            store.add_schedule(
                schedule_id=make_schedule_id(), name="unique",
                cron_expr="0 4 * * *", docs_path="/b",
            )


class TestScheduleRunTracking:
    def test_update_schedule_run_with_next(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="run-test",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        store.update_schedule_run(
            schedule_id=sid,
            last_run_at=1000.0,
            last_run_status="triggered",
            next_run_at=2000.0,
        )
        s = store.get_schedule(sid)
        assert s["last_run_at"] == 1000.0
        assert s["last_run_status"] == "triggered"
        assert s["next_run_at"] == 2000.0

    def test_update_schedule_run_without_next(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="run-test-no-next",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        store.update_schedule_run(
            schedule_id=sid,
            last_run_at=1000.0,
            last_run_status="error",
        )
        s = store.get_schedule(sid)
        assert s["last_run_at"] == 1000.0
        assert s["last_run_status"] == "error"
        assert s["next_run_at"] is None

    def test_get_enabled_schedules_due(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="due-test",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        due = store.get_enabled_schedules_due()
        assert len(due) == 1
        assert due[0]["id"] == sid

    def test_get_enabled_schedules_due_excludes_disabled(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="disabled-test",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        store.update_schedule(schedule_id=sid, enabled=False)
        due = store.get_enabled_schedules_due()
        assert len(due) == 0

    def test_get_enabled_schedules_due_excludes_future(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="future-test",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        store.update_schedule_run(
            schedule_id=sid,
            last_run_at=1000.0,
            last_run_status="triggered",
            next_run_at=999999999999.0,
        )
        due = store.get_enabled_schedules_due()
        assert len(due) == 0

    def test_get_enabled_schedules_due_null_next_run(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="null-next-test",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        due = store.get_enabled_schedules_due()
        assert len(due) == 1

    def test_get_enabled_schedules_due_past_next_run(self, store):
        sid = make_schedule_id()
        store.add_schedule(
            schedule_id=sid, name="past-next-test",
            cron_expr="0 3 * * *", docs_path="/data",
        )
        store.update_schedule_run(
            schedule_id=sid,
            last_run_at=1000.0,
            last_run_status="triggered",
            next_run_at=1.0,
        )
        due = store.get_enabled_schedules_due()
        assert len(due) == 1


class TestScheduleSchema:
    def test_schema_version_after_connect(self, temp_db):
        store = MetadataStore(db_path=temp_db)
        store.connect()
        row = store.conn.execute(
            "SELECT version FROM schema_version"
        ).fetchone()
        assert row["version"] == 6
        store.close()

    def test_schedules_table_exists(self, store):
        tables = store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {r[0] for r in tables}
        assert "schedules" in table_names
