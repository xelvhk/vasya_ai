from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping, Protocol


_CONNECTOR_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ConnectorAccess(str, Enum):
    READ = "read"
    MUTATING = "mutating"


class ConnectorExecution(str, Enum):
    DIRECT = "direct"
    APPROVAL_QUEUE = "approval_queue"


class ConnectorAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ConnectorSetup(str, Enum):
    CONFIGURED = "configured"
    NOT_CONFIGURED = "not_configured"
    NOT_REQUIRED = "not_required"
    UNKNOWN = "unknown"


class ConnectorPermission(str, Enum):
    GRANTED = "granted"
    NOT_REQUESTED = "not_requested"
    DENIED = "denied"
    RESTRICTED = "restricted"
    NOT_REQUIRED = "not_required"
    NOT_SUPPORTED = "not_supported"
    UNKNOWN = "unknown"


class ConnectorHealth(str, Enum):
    READY = "ready"
    SETUP_REQUIRED = "setup_required"
    PERMISSION_REQUIRED = "permission_required"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class ConnectorCapability:
    id: str
    access: ConnectorAccess
    execution: ConnectorExecution

    def __post_init__(self) -> None:
        _validate_identifier(self.id, field="capability id")
        if (
            self.access is ConnectorAccess.MUTATING
            and self.execution is not ConnectorExecution.APPROVAL_QUEUE
        ):
            raise ValueError("mutating connector capabilities must use the approval queue")


@dataclass(frozen=True)
class ConnectorDescriptor:
    id: str
    display_name: str
    capabilities: tuple[ConnectorCapability, ...]

    def __post_init__(self) -> None:
        _validate_identifier(self.id, field="connector id")
        if not self.display_name.strip():
            raise ValueError("connector display name must not be empty")
        capability_ids = [capability.id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError(f"duplicate capability id for connector: {self.id}")

    @property
    def read_capability_ids(self) -> tuple[str, ...]:
        return tuple(
            capability.id
            for capability in self.capabilities
            if capability.access is ConnectorAccess.READ
        )

    @property
    def mutating_capability_ids(self) -> tuple[str, ...]:
        return tuple(
            capability.id
            for capability in self.capabilities
            if capability.access is ConnectorAccess.MUTATING
        )


@dataclass(frozen=True)
class ConnectorReadiness:
    connector_id: str
    availability: ConnectorAvailability
    setup: ConnectorSetup
    permission: ConnectorPermission
    health: ConnectorHealth
    detail: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier(self.connector_id, field="connector id")
        if self.detail is not None and not self.detail.strip():
            raise ValueError("connector readiness detail must not be empty")


@dataclass(frozen=True)
class ConnectorProvenance:
    connector_id: str
    source_type: str
    source_id: str
    project_id: str | None
    synced_at: datetime

    def __post_init__(self) -> None:
        _validate_identifier(self.connector_id, field="connector id")
        _validate_identifier(self.source_type, field="source type")
        if not self.source_id.strip():
            raise ValueError("source id must not be empty")
        if self.project_id is not None and not self.project_id.strip():
            raise ValueError("project id must not be empty")
        _validate_timezone(self.synced_at, field="provenance synced_at")


@dataclass(frozen=True)
class ConnectorSyncCursor:
    connector_id: str
    value: str
    synced_at: datetime

    def __post_init__(self) -> None:
        _validate_identifier(self.connector_id, field="connector id")
        if not self.value:
            raise ValueError("sync cursor value must not be empty")
        _validate_timezone(self.synced_at, field="sync cursor synced_at")


@dataclass(frozen=True)
class ConnectorRecord:
    record_type: str
    provenance: ConnectorProvenance
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        _validate_identifier(self.record_type, field="record type")


@dataclass(frozen=True)
class ConnectorReadBatch:
    connector_id: str
    records: tuple[ConnectorRecord, ...]
    next_cursor: ConnectorSyncCursor | None

    def __post_init__(self) -> None:
        _validate_identifier(self.connector_id, field="connector id")
        if any(
            record.provenance.connector_id != self.connector_id
            for record in self.records
        ):
            raise ValueError("read batch records must belong to one connector")
        if (
            self.next_cursor is not None
            and self.next_cursor.connector_id != self.connector_id
        ):
            raise ValueError("read batch cursor must belong to the connector")


class ProjectConnector(Protocol):
    descriptor: ConnectorDescriptor

    def inspect_readiness(self) -> ConnectorReadiness: ...

    def read(self, cursor: ConnectorSyncCursor | None = None) -> ConnectorReadBatch: ...


def _validate_identifier(value: str, *, field: str) -> None:
    if not isinstance(value, str) or not _CONNECTOR_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase stable identifier")


def _validate_timezone(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
