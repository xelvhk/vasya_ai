from __future__ import annotations

from datetime import datetime, timezone
import unittest

from interfaces.project_connectors import (
    ConnectorAccess,
    ConnectorAvailability,
    ConnectorCapability,
    ConnectorDescriptor,
    ConnectorExecution,
    ConnectorHealth,
    ConnectorPermission,
    ConnectorProvenance,
    ConnectorReadBatch,
    ConnectorReadiness,
    ConnectorRecord,
    ConnectorSetup,
    ConnectorSyncCursor,
)
from services.project_connector_service import ProjectConnectorRegistry


class _FakeConnector:
    def __init__(
        self,
        connector_id: str,
        *,
        readiness: ConnectorReadiness | None = None,
        inspect_error: Exception | None = None,
    ) -> None:
        self.descriptor = ConnectorDescriptor(
            id=connector_id,
            display_name=connector_id.title(),
            capabilities=(
                ConnectorCapability(
                    id="tasks.read",
                    access=ConnectorAccess.READ,
                    execution=ConnectorExecution.DIRECT,
                ),
            ),
        )
        self._readiness = readiness or ConnectorReadiness(
            connector_id=connector_id,
            availability=ConnectorAvailability.AVAILABLE,
            setup=ConnectorSetup.CONFIGURED,
            permission=ConnectorPermission.GRANTED,
            health=ConnectorHealth.READY,
        )
        self._inspect_error = inspect_error
        self.inspect_calls = 0
        self.read_calls = 0

    def inspect_readiness(self) -> ConnectorReadiness:
        self.inspect_calls += 1
        if self._inspect_error is not None:
            raise self._inspect_error
        return self._readiness

    def read(self, cursor: ConnectorSyncCursor | None = None) -> ConnectorReadBatch:
        self.read_calls += 1
        raise AssertionError("read must not run during readiness inspection")


class ProjectConnectorContractTests(unittest.TestCase):
    def test_capabilities_separate_read_and_approval_queued_mutations(self) -> None:
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
                    id="tasks.complete",
                    access=ConnectorAccess.MUTATING,
                    execution=ConnectorExecution.APPROVAL_QUEUE,
                ),
            ),
        )

        self.assertEqual(descriptor.read_capability_ids, ("tasks.read",))
        self.assertEqual(descriptor.mutating_capability_ids, ("tasks.complete",))

    def test_mutating_capability_cannot_execute_directly(self) -> None:
        with self.assertRaisesRegex(ValueError, "approval queue"):
            ConnectorCapability(
                id="tasks.complete",
                access=ConnectorAccess.MUTATING,
                execution=ConnectorExecution.DIRECT,
            )

    def test_readiness_listing_does_not_start_connector_reads(self) -> None:
        ready = _FakeConnector("github")
        unavailable = _FakeConnector(
            "eva",
            readiness=ConnectorReadiness(
                connector_id="eva",
                availability=ConnectorAvailability.UNAVAILABLE,
                setup=ConnectorSetup.NOT_CONFIGURED,
                permission=ConnectorPermission.NOT_SUPPORTED,
                health=ConnectorHealth.UNAVAILABLE,
                detail="EventKit is available only on macOS.",
            ),
        )
        registry = ProjectConnectorRegistry((ready, unavailable))

        descriptors = registry.list_descriptors()
        statuses = registry.list_readiness()

        self.assertEqual([item.id for item in descriptors], ["eva", "github"])
        self.assertEqual(descriptors[0].read_capability_ids, ("tasks.read",))
        self.assertEqual([status.connector_id for status in statuses], ["eva", "github"])
        self.assertEqual(statuses[0].health, ConnectorHealth.UNAVAILABLE)
        self.assertEqual(statuses[0].detail, "EventKit is available only on macOS.")
        self.assertEqual(ready.inspect_calls, 1)
        self.assertEqual(unavailable.inspect_calls, 1)
        self.assertEqual(ready.read_calls, 0)
        self.assertEqual(unavailable.read_calls, 0)

    def test_readiness_failure_is_reported_as_degraded_status(self) -> None:
        connector = _FakeConnector(
            "broken",
            inspect_error=RuntimeError("provider exploded"),
        )

        status = ProjectConnectorRegistry((connector,)).list_readiness()[0]

        self.assertEqual(status.connector_id, "broken")
        self.assertEqual(status.availability, ConnectorAvailability.AVAILABLE)
        self.assertEqual(status.health, ConnectorHealth.DEGRADED)
        self.assertEqual(status.detail, "connector readiness check failed")

    def test_registry_rejects_duplicate_connector_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate connector id"):
            ProjectConnectorRegistry((_FakeConnector("eva"), _FakeConnector("eva")))

    def test_read_batch_preserves_source_identity_cursor_and_sync_time(self) -> None:
        synced_at = datetime(2026, 8, 26, 8, 30, tzinfo=timezone.utc)
        provenance = ConnectorProvenance(
            connector_id="eva",
            source_type="apple_reminder",
            source_id="reminder-42",
            project_id="ai-pal",
            synced_at=synced_at,
        )
        cursor = ConnectorSyncCursor(
            connector_id="eva",
            value="cursor-7",
            synced_at=synced_at,
        )
        batch = ConnectorReadBatch(
            connector_id="eva",
            records=(
                ConnectorRecord(
                    record_type="task",
                    provenance=provenance,
                    payload={"title": "Review connector contract", "completed": False},
                ),
            ),
            next_cursor=cursor,
        )

        self.assertEqual(batch.records[0].provenance.source_id, "reminder-42")
        self.assertEqual(batch.records[0].provenance.project_id, "ai-pal")
        self.assertEqual(batch.next_cursor, cursor)

    def test_read_batch_rejects_records_from_another_connector(self) -> None:
        synced_at = datetime(2026, 8, 26, 8, 30, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "one connector"):
            ConnectorReadBatch(
                connector_id="eva",
                records=(
                    ConnectorRecord(
                        record_type="task",
                        provenance=ConnectorProvenance(
                            connector_id="github",
                            source_type="issue",
                            source_id="issue-42",
                            project_id="ai-pal",
                            synced_at=synced_at,
                        ),
                        payload={"title": "Wrong source"},
                    ),
                ),
                next_cursor=None,
            )

    def test_provenance_requires_timezone_aware_sync_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            ConnectorProvenance(
                connector_id="eva",
                source_type="apple_reminder",
                source_id="reminder-42",
                project_id=None,
                synced_at=datetime(2026, 8, 26, 8, 30),
            )


if __name__ == "__main__":
    unittest.main()
