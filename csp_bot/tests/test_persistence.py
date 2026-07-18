"""Tests for bot runtime persistence helpers."""

from datetime import datetime, timedelta, timezone

from chatom import Message, User

from csp_bot.persistence import FsspecStateStore, InMemoryStateStore, ScheduledCommandRecord, ScheduleStore, StoredRecord
from csp_bot.structs import BotCommand, CommandVariant


def _make_command(command: str = "echo", message_id: str = "msg1") -> BotCommand:
    return BotCommand(
        command=command,
        args=("hello",),
        source=User(id="U123", name="Test User"),
        targets=(),
        channel_id="C456",
        channel_name="general",
        backend="slack",
        variant=CommandVariant.REPLY,
        message=Message(id=message_id, content=f"/{command} hello"),
        delay=datetime.now(timezone.utc) + timedelta(minutes=5),
        schedule="",
        times_run=0,
    )


class TestInMemoryStateStore:
    def test_stored_record_expiry_boundaries(self):
        now = datetime.now(timezone.utc)

        assert StoredRecord("namespace", "never", "value", now, now).is_expired(now) is False
        assert StoredRecord("namespace", "future", "value", now, now, now + timedelta(seconds=1)).is_expired(now) is False
        assert StoredRecord("namespace", "now", "value", now, now, now).is_expired(now) is True
        assert StoredRecord("namespace", "past", "value", now, now, now - timedelta(seconds=1)).is_expired(now) is True

    def test_put_and_get(self):
        store = InMemoryStateStore()

        store.put("namespace", "key", {"value": 1})

        assert store.get("namespace", "key") == {"value": 1}

    def test_get_returns_default_for_missing_key(self):
        store = InMemoryStateStore()

        assert store.get("namespace", "missing", default="fallback") == "fallback"

    def test_ttl_expiry_removes_record_on_get(self):
        store = InMemoryStateStore()
        store.put("namespace", "key", "value", ttl_seconds=-1)

        assert store.get("namespace", "key") is None
        assert store.records("namespace") == []

    def test_ttl_zero_expires_immediately(self):
        store = InMemoryStateStore()
        store.put("namespace", "key", "value", ttl_seconds=0)

        assert store.get("namespace", "key") is None

    def test_records_filters_by_namespace_and_prefix(self):
        store = InMemoryStateStore()
        store.put("schedules", "slack:1", 1)
        store.put("schedules", "slack:2", 2)
        store.put("schedules", "discord:1", 3)
        store.put("sessions", "slack:1", 4)

        records = store.records("schedules", prefix="slack:")

        assert [record.value for record in records] == [1, 2]

    def test_cleanup_expired_can_target_namespace(self):
        store = InMemoryStateStore()
        store.put("schedules", "expired", 1, ttl_seconds=-1)
        store.put("sessions", "expired", 2, ttl_seconds=-1)

        removed = store.cleanup_expired("schedules")

        assert removed == 1
        assert store.records("schedules") == []
        assert store.get("sessions", "expired") is None

    def test_overwrite_preserves_created_at_and_updates_updated_at(self):
        store = InMemoryStateStore()
        first = store.put("namespace", "key", "first")
        second = store.put("namespace", "key", "second")

        assert second.created_at == first.created_at
        assert second.updated_at >= first.updated_at
        assert store.get("namespace", "key") == "second"


class TestFsspecStateStore:
    def test_persists_across_instances(self, tmp_path):
        url = str(tmp_path / "state")
        first = FsspecStateStore(url)
        first.put("namespace", "key", {"value": 1})

        second = FsspecStateStore(url)

        assert second.get("namespace", "key") == {"value": 1}

    def test_records_filters_by_namespace_and_prefix(self, tmp_path):
        store = FsspecStateStore(str(tmp_path / "state"))
        store.put("schedules", "slack:1", 1)
        store.put("schedules", "slack:2", 2)
        store.put("schedules", "discord:1", 3)
        store.put("sessions", "slack:1", 4)

        records = store.records("schedules", prefix="slack:")

        assert [record.value for record in records] == [1, 2]

    def test_ttl_expiry_removes_record_on_get(self, tmp_path):
        store = FsspecStateStore(str(tmp_path / "state"))
        store.put("namespace", "key", "value", ttl_seconds=0)

        assert store.get("namespace", "key") is None
        assert store.records("namespace") == []

    def test_clear_namespace(self, tmp_path):
        store = FsspecStateStore(str(tmp_path / "state"))
        store.put("schedules", "one", 1)
        store.put("sessions", "one", 2)

        assert store.clear("schedules") == 1
        assert store.records("schedules") == []
        assert store.get("sessions", "one") == 2


class TestScheduleStore:
    def test_put_and_get_schedule_record(self):
        store = ScheduleStore(InMemoryStateStore())
        command = _make_command()

        record = store.put(command, schedule_id="schedule-1")

        assert isinstance(record, ScheduledCommandRecord)
        assert store.get("schedule-1") == record
        assert record.command.command == command.command
        assert record.command.message.id == command.message.id
        assert record.command.schedule_id == "schedule-1"
        assert record.next_run_at == command.delay.replace(tzinfo=timezone.utc)

    def test_generated_ids_allow_same_command_name(self):
        store = ScheduleStore(InMemoryStateStore())
        first = _make_command(command="echo", message_id="msg1")
        second = _make_command(command="echo", message_id="msg2")

        first_record = store.put(first)
        second_record = store.put(second)

        assert first_record.schedule_id != second_record.schedule_id
        assert [record.command.message.id for record in store.records()] == [first.message.id, second.message.id]

    def test_remove_schedule_record(self):
        store = ScheduleStore(InMemoryStateStore())
        store.put(_make_command(), schedule_id="schedule-1")

        assert store.remove("schedule-1") is True
        assert store.get("schedule-1") is None

    def test_recurring_record_uses_command_schedule(self):
        store = ScheduleStore(InMemoryStateStore())
        command = _make_command()
        command.schedule = "*/5 * * * *"

        record = store.put(command, schedule_id="recurring")

        assert record.is_recurring is True

    def test_next_run_override(self):
        store = ScheduleStore(InMemoryStateStore())
        command = _make_command()
        next_run_at = datetime.now(timezone.utc) + timedelta(hours=1)

        record = store.put(command, schedule_id="schedule-1", next_run_at=next_run_at)

        assert record.next_run_at == next_run_at

    def test_created_at_preserved_across_updates(self):
        store = ScheduleStore(InMemoryStateStore())
        command = _make_command()
        first = store.put(command, schedule_id="schedule-1")
        command.args = ("updated",)
        second = store.put(command, schedule_id="schedule-1")

        assert second.created_at == first.created_at
        assert second.updated_at >= first.updated_at
        assert second.command.args == ("updated",)

    def test_cleanup_expired(self):
        store = ScheduleStore(InMemoryStateStore())
        store.put(_make_command(), schedule_id="expired", ttl_seconds=-1)

        assert store.cleanup_expired() == 1
        assert store.records() == []

    def test_fsspec_round_trips_scheduled_command(self, tmp_path):
        url = str(tmp_path / "state")
        first = ScheduleStore(FsspecStateStore(url))
        command = _make_command(command="echo", message_id="msg1")
        first.put(command, schedule_id="schedule-1")

        second = ScheduleStore(FsspecStateStore(url))
        record = second.get("schedule-1")

        assert record is not None
        assert record.schedule_id == "schedule-1"
        assert record.command.command == "echo"
        assert record.command.message.id == "msg1"
        assert record.command.source.id == "U123"
