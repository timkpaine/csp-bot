"""Persistence primitives for bot runtime state.

The first implementation is in-memory so existing behavior stays simple, but the
protocol is shaped for durable backends such as SQLite or Redis.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pickle import HIGHEST_PROTOCOL, dumps, loads
from typing import Any, Iterable, Optional, Protocol
from urllib.parse import quote, unquote

from csp_bot.structs import BotCommand

__all__ = (
    "FsspecStateStore",
    "InMemoryStateStore",
    "ScheduleStore",
    "ScheduledCommandRecord",
    "StateStore",
    "StoredRecord",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _sort_datetime(value: Optional[datetime]) -> datetime:
    return _to_utc(value) or datetime.max.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class StoredRecord:
    """A single namespaced state record."""

    namespace: str
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        return (_to_utc(now) or _utc_now()) >= _to_utc(self.expires_at)


class StateStore(Protocol):
    """Namespace/key/value persistence interface for bot runtime state."""

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Return a value, or default if missing or expired."""
        ...

    def put(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[float] = None) -> StoredRecord:
        """Store a value with an optional TTL and return its record metadata.

        A TTL of ``None`` means no expiry. A TTL of ``0`` expires immediately.
        """
        ...

    def delete(self, namespace: str, key: str) -> bool:
        """Delete a value and return whether a record was removed."""
        ...

    def records(self, namespace: str, prefix: str = "") -> Iterable[StoredRecord]:
        """Return unexpired records in a namespace, optionally filtered by key prefix."""
        ...

    def cleanup_expired(self, namespace: Optional[str] = None) -> int:
        """Remove expired records and return the number removed."""
        ...

    def clear(self, namespace: Optional[str] = None) -> int:
        """Remove records, optionally limited to one namespace."""
        ...


class InMemoryStateStore:
    """Thread-safe in-memory StateStore implementation.

    Values are stored by reference. Durable implementations are expected to
    serialize or copy values at the storage boundary.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], StoredRecord] = {}
        self._lock = threading.Lock()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            record_key = (namespace, key)
            record = self._records.get(record_key)
            if record is None:
                return default
            if record.is_expired():
                self._records.pop(record_key, None)
                return default
            return record.value

    def put(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[float] = None) -> StoredRecord:
        now = _utc_now()
        record_key = (namespace, key)
        with self._lock:
            existing = self._records.get(record_key)
            expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
            record = StoredRecord(
                namespace=namespace,
                key=key,
                value=value,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                expires_at=_to_utc(expires_at),
            )
            self._records[record_key] = record
            return record

    def delete(self, namespace: str, key: str) -> bool:
        with self._lock:
            return self._records.pop((namespace, key), None) is not None

    def records(self, namespace: str, prefix: str = "") -> list[StoredRecord]:
        # Cleanup and read are separate lock acquisitions; this keeps the
        # StateStore protocol simple for backends with native expiry support.
        self.cleanup_expired(namespace)
        with self._lock:
            return [
                record
                for (record_namespace, record_key), record in sorted(self._records.items())
                if record_namespace == namespace and record_key.startswith(prefix)
            ]

    def cleanup_expired(self, namespace: Optional[str] = None) -> int:
        now = _utc_now()
        with self._lock:
            expired_keys = [
                record_key
                for record_key, record in self._records.items()
                if (namespace is None or record.namespace == namespace) and record.is_expired(now)
            ]
            for record_key in expired_keys:
                self._records.pop(record_key, None)
            return len(expired_keys)

    def clear(self, namespace: Optional[str] = None) -> int:
        """Remove records, optionally limited to one namespace."""
        with self._lock:
            if namespace is None:
                removed = len(self._records)
                self._records.clear()
                return removed
            removed_keys = [record_key for record_key, record in self._records.items() if record.namespace == namespace]
            for record_key in removed_keys:
                self._records.pop(record_key, None)
            return len(removed_keys)


class FsspecStateStore:
    """fsspec-backed StateStore implementation.

    Records are stored as one pickle payload per namespace/key below ``url``.
    Pickle keeps this backend compatible with the current ``StateStore`` value
    contract, which accepts arbitrary Python objects. Only use this store with
    trusted storage locations and compatible csp-bot/chatom versions.
    """

    def __init__(self, url: str, **storage_options: Any) -> None:
        import fsspec

        self._mapper = fsspec.get_mapper(url, create=True, **storage_options)
        self._lock = threading.Lock()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            map_key = self._map_key(namespace, key)
            record = self._load_record(map_key)
            if record is None:
                return default
            if record.is_expired():
                self._delete_map_key(map_key)
                return default
            return record.value

    def put(self, namespace: str, key: str, value: Any, ttl_seconds: Optional[float] = None) -> StoredRecord:
        now = _utc_now()
        map_key = self._map_key(namespace, key)
        with self._lock:
            existing = self._load_record(map_key)
            expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
            record = StoredRecord(
                namespace=namespace,
                key=key,
                value=value,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                expires_at=_to_utc(expires_at),
            )
            self._mapper[map_key] = dumps(record, protocol=HIGHEST_PROTOCOL)
            return record

    def delete(self, namespace: str, key: str) -> bool:
        with self._lock:
            return self._delete_map_key(self._map_key(namespace, key))

    def records(self, namespace: str, prefix: str = "") -> list[StoredRecord]:
        self.cleanup_expired(namespace)
        encoded_namespace = self._encode(namespace)
        with self._lock:
            records = []
            for map_key in sorted(self._mapper.keys()):
                if not map_key.startswith(f"{encoded_namespace}/"):
                    continue
                record = self._load_record(map_key)
                if record and record.key.startswith(prefix):
                    records.append(record)
            return records

    def cleanup_expired(self, namespace: Optional[str] = None) -> int:
        now = _utc_now()
        encoded_namespace = self._encode(namespace) if namespace is not None else None
        with self._lock:
            expired_keys = []
            for map_key in list(self._mapper.keys()):
                if encoded_namespace is not None and not map_key.startswith(f"{encoded_namespace}/"):
                    continue
                record = self._load_record(map_key)
                if record and record.is_expired(now):
                    expired_keys.append(map_key)
            for map_key in expired_keys:
                self._delete_map_key(map_key)
            return len(expired_keys)

    def clear(self, namespace: Optional[str] = None) -> int:
        with self._lock:
            if namespace is None:
                keys = list(self._mapper.keys())
            else:
                encoded_namespace = self._encode(namespace)
                keys = [map_key for map_key in self._mapper.keys() if map_key.startswith(f"{encoded_namespace}/")]
            for map_key in keys:
                self._delete_map_key(map_key)
            return len(keys)

    @staticmethod
    def _encode(value: str) -> str:
        return quote(value, safe="")

    @staticmethod
    def _decode(value: str) -> str:
        return unquote(value)

    @classmethod
    def _map_key(cls, namespace: str, key: str) -> str:
        return f"{cls._encode(namespace)}/{cls._encode(key)}"

    def _load_record(self, map_key: str) -> Optional[StoredRecord]:
        try:
            data = self._mapper[map_key]
        except KeyError:
            return None
        record = loads(bytes(data))
        if not isinstance(record, StoredRecord):
            raise TypeError(f"Stored value is not a StoredRecord: {map_key}")
        return record

    def _delete_map_key(self, map_key: str) -> bool:
        try:
            del self._mapper[map_key]
        except KeyError:
            return False
        return True


@dataclass(frozen=True)
class ScheduledCommandRecord:
    """Persistent representation of a scheduled bot command."""

    schedule_id: str
    command: BotCommand
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @property
    def is_recurring(self) -> bool:
        return bool(self.command.schedule)


class ScheduleStore:
    """Typed repository for scheduled BotCommand state."""

    namespace = "csp_bot.schedules"

    def __init__(self, store: StateStore) -> None:
        self._store = store

    def put(
        self,
        command: BotCommand,
        schedule_id: Optional[str] = None,
        next_run_at: Optional[datetime] = None,
        ttl_seconds: Optional[float] = None,
    ) -> ScheduledCommandRecord:
        """Store a scheduled command.

        If no schedule ID is provided, a new ID is generated and assigned back
        to ``command.schedule_id`` so the command carried by CSP alarms can be
        matched against the stored record when it fires.
        """
        now = _utc_now()
        resolved_schedule_id = schedule_id or getattr(command, "schedule_id", "") or uuid.uuid4().hex
        command.schedule_id = resolved_schedule_id
        existing = self.get(resolved_schedule_id)
        record = ScheduledCommandRecord(
            schedule_id=resolved_schedule_id,
            command=command,
            next_run_at=_to_utc(next_run_at if next_run_at is not None else command.delay),
            created_at=_to_utc(existing.created_at) if existing else now,
            updated_at=now,
        )
        self._store.put(self.namespace, resolved_schedule_id, record, ttl_seconds=ttl_seconds)
        return record

    def get(self, schedule_id: str) -> Optional[ScheduledCommandRecord]:
        record = self._store.get(self.namespace, schedule_id)
        if isinstance(record, ScheduledCommandRecord):
            return record
        return None

    def remove(self, schedule_id: str) -> bool:
        return self._store.delete(self.namespace, schedule_id)

    def records(self) -> list[ScheduledCommandRecord]:
        records = [record.value for record in self._store.records(self.namespace) if isinstance(record.value, ScheduledCommandRecord)]
        return sorted(records, key=lambda record: (_sort_datetime(record.next_run_at), _sort_datetime(record.created_at), record.schedule_id))

    def cleanup_expired(self) -> int:
        return self._store.cleanup_expired(self.namespace)
