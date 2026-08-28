from __future__ import annotations

import importlib.util
from typing import Protocol

from interfaces.project_connectors import (
    ConnectorAccess,
    ConnectorAvailability,
    ConnectorCapability,
    ConnectorDescriptor,
    ConnectorExecution,
    ConnectorHealth,
    ConnectorPermission,
    ConnectorReadBatch,
    ConnectorReadiness,
    ConnectorSetup,
    ConnectorSyncCursor,
)
from utils.platform_runtime import PlatformName, get_platform_name


class EventKitFrameworkProbe(Protocol):
    def is_available(self) -> bool: ...


class PythonEventKitFrameworkProbe:
    """Checks for the PyObjC bridge without importing EventKit."""

    def is_available(self) -> bool:
        return importlib.util.find_spec("EventKit") is not None


class EvaEventKitReadUnavailableError(RuntimeError):
    pass


class EvaEventKitConnector:
    descriptor = ConnectorDescriptor(
        id="eva",
        display_name="Eva via Apple",
        capabilities=(
            ConnectorCapability(
                id="tasks.read",
                access=ConnectorAccess.READ,
                execution=ConnectorExecution.DIRECT,
            ),
            ConnectorCapability(
                id="events.read",
                access=ConnectorAccess.READ,
                execution=ConnectorExecution.DIRECT,
            ),
        ),
    )

    def __init__(
        self,
        *,
        platform_name: PlatformName | None = None,
        framework_probe: EventKitFrameworkProbe | None = None,
    ) -> None:
        self._platform_name = platform_name or get_platform_name()
        self._framework_probe = framework_probe or PythonEventKitFrameworkProbe()

    def inspect_readiness(self) -> ConnectorReadiness:
        if self._platform_name != "macos":
            return ConnectorReadiness(
                connector_id=self.descriptor.id,
                availability=ConnectorAvailability.UNAVAILABLE,
                setup=ConnectorSetup.NOT_REQUIRED,
                permission=ConnectorPermission.NOT_SUPPORTED,
                health=ConnectorHealth.UNAVAILABLE,
                detail="EventKit is available only on macOS.",
            )

        if not self._framework_probe.is_available():
            return ConnectorReadiness(
                connector_id=self.descriptor.id,
                availability=ConnectorAvailability.UNAVAILABLE,
                setup=ConnectorSetup.NOT_CONFIGURED,
                permission=ConnectorPermission.NOT_SUPPORTED,
                health=ConnectorHealth.UNAVAILABLE,
                detail="The PyObjC EventKit bridge is not installed.",
            )

        return ConnectorReadiness(
            connector_id=self.descriptor.id,
            availability=ConnectorAvailability.AVAILABLE,
            setup=ConnectorSetup.NOT_CONFIGURED,
            permission=ConnectorPermission.NOT_REQUESTED,
            health=ConnectorHealth.PERMISSION_REQUIRED,
            detail=(
                "Choose Eva-synced lists and calendars, "
                "then grant EventKit access."
            ),
        )

    def read(
        self,
        cursor: ConnectorSyncCursor | None = None,
    ) -> ConnectorReadBatch:
        _ = cursor
        raise EvaEventKitReadUnavailableError(
            "EventKit reads are not enabled until connector setup, "
            "permission handling, and record normalization are implemented."
        )
