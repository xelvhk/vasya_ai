from __future__ import annotations

from collections.abc import Iterable

from interfaces.project_connectors import (
    ConnectorAvailability,
    ConnectorDescriptor,
    ConnectorHealth,
    ConnectorPermission,
    ConnectorReadiness,
    ConnectorSetup,
    ProjectConnector,
)


class ProjectConnectorRegistry:
    """Registry and lightweight readiness view for Project OS connectors."""

    def __init__(self, connectors: Iterable[ProjectConnector] = ()) -> None:
        connector_by_id: dict[str, ProjectConnector] = {}
        for connector in connectors:
            connector_id = connector.descriptor.id
            if connector_id in connector_by_id:
                raise ValueError(f"duplicate connector id: {connector_id}")
            connector_by_id[connector_id] = connector
        self._connector_by_id = connector_by_id

    def list_descriptors(self) -> tuple[ConnectorDescriptor, ...]:
        return tuple(
            connector.descriptor
            for connector in sorted(
                self._connector_by_id.values(),
                key=lambda item: item.descriptor.id,
            )
        )

    def list_readiness(self) -> tuple[ConnectorReadiness, ...]:
        return tuple(
            self._inspect(connector)
            for connector in sorted(
                self._connector_by_id.values(),
                key=lambda item: item.descriptor.id,
            )
        )

    @staticmethod
    def _inspect(connector: ProjectConnector) -> ConnectorReadiness:
        try:
            readiness = connector.inspect_readiness()
        except Exception:
            return ConnectorReadiness(
                connector_id=connector.descriptor.id,
                availability=ConnectorAvailability.AVAILABLE,
                setup=ConnectorSetup.UNKNOWN,
                permission=ConnectorPermission.UNKNOWN,
                health=ConnectorHealth.DEGRADED,
                detail="connector readiness check failed",
            )
        if readiness.connector_id != connector.descriptor.id:
            return ConnectorReadiness(
                connector_id=connector.descriptor.id,
                availability=ConnectorAvailability.AVAILABLE,
                setup=ConnectorSetup.UNKNOWN,
                permission=ConnectorPermission.UNKNOWN,
                health=ConnectorHealth.DEGRADED,
                detail="connector readiness identity mismatch",
            )
        return readiness
