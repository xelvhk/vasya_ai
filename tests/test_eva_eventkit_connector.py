from __future__ import annotations

import unittest
from unittest.mock import patch

from interfaces.project_connectors import (
    ConnectorAvailability,
    ConnectorHealth,
    ConnectorPermission,
    ConnectorSetup,
)
from services.eva_eventkit_connector import (
    EvaEventKitConnector,
    EvaEventKitReadUnavailableError,
    PythonEventKitFrameworkProbe,
)


class _FakeFrameworkProbe:
    def __init__(self, available: bool) -> None:
        self.available = available
        self.calls = 0

    def is_available(self) -> bool:
        self.calls += 1
        return self.available


class EvaEventKitConnectorTests(unittest.TestCase):
    def test_descriptor_exposes_read_only_task_and_event_capabilities(self) -> None:
        connector = EvaEventKitConnector(
            platform_name="macos",
            framework_probe=_FakeFrameworkProbe(True),
        )

        self.assertEqual(connector.descriptor.id, "eva")
        self.assertEqual(connector.descriptor.display_name, "Eva via Apple")
        self.assertEqual(
            connector.descriptor.read_capability_ids,
            ("tasks.read", "events.read"),
        )
        self.assertEqual(connector.descriptor.mutating_capability_ids, ())

    def test_non_macos_is_unavailable_without_probing_eventkit(self) -> None:
        for platform_name in ("windows", "linux", "unknown"):
            with self.subTest(platform_name=platform_name):
                probe = _FakeFrameworkProbe(True)
                connector = EvaEventKitConnector(
                    platform_name=platform_name,
                    framework_probe=probe,
                )

                readiness = connector.inspect_readiness()

                self.assertEqual(probe.calls, 0)
                self.assertEqual(
                    readiness.availability,
                    ConnectorAvailability.UNAVAILABLE,
                )
                self.assertEqual(readiness.setup, ConnectorSetup.NOT_REQUIRED)
                self.assertEqual(
                    readiness.permission,
                    ConnectorPermission.NOT_SUPPORTED,
                )
                self.assertEqual(readiness.health, ConnectorHealth.UNAVAILABLE)
                self.assertEqual(
                    readiness.detail,
                    "EventKit is available only on macOS.",
                )

    def test_macos_without_eventkit_bridge_is_unavailable(self) -> None:
        connector = EvaEventKitConnector(
            platform_name="macos",
            framework_probe=_FakeFrameworkProbe(False),
        )

        readiness = connector.inspect_readiness()

        self.assertEqual(readiness.availability, ConnectorAvailability.UNAVAILABLE)
        self.assertEqual(readiness.setup, ConnectorSetup.NOT_CONFIGURED)
        self.assertEqual(readiness.permission, ConnectorPermission.NOT_SUPPORTED)
        self.assertEqual(readiness.health, ConnectorHealth.UNAVAILABLE)
        self.assertEqual(
            readiness.detail,
            "The PyObjC EventKit bridge is not installed.",
        )

    def test_macos_with_eventkit_reports_opt_in_permission_required(self) -> None:
        connector = EvaEventKitConnector(
            platform_name="macos",
            framework_probe=_FakeFrameworkProbe(True),
        )

        readiness = connector.inspect_readiness()

        self.assertEqual(readiness.availability, ConnectorAvailability.AVAILABLE)
        self.assertEqual(readiness.setup, ConnectorSetup.NOT_CONFIGURED)
        self.assertEqual(readiness.permission, ConnectorPermission.NOT_REQUESTED)
        self.assertEqual(readiness.health, ConnectorHealth.PERMISSION_REQUIRED)
        self.assertEqual(
            readiness.detail,
            "Choose Eva-synced lists and calendars, then grant EventKit access.",
        )

    def test_read_fails_closed_until_permission_and_reader_slice_exists(self) -> None:
        connector = EvaEventKitConnector(
            platform_name="macos",
            framework_probe=_FakeFrameworkProbe(True),
        )

        with self.assertRaisesRegex(
            EvaEventKitReadUnavailableError,
            "not enabled",
        ):
            connector.read()

    def test_python_probe_checks_module_without_importing_eventkit(self) -> None:
        probe = PythonEventKitFrameworkProbe()

        with patch(
            "services.eva_eventkit_connector.importlib.util.find_spec",
            return_value=object(),
        ) as find_spec:
            self.assertTrue(probe.is_available())

        find_spec.assert_called_once_with("EventKit")


if __name__ == "__main__":
    unittest.main()
