from __future__ import annotations

import unittest

from core.ports import AppPorts, build_default_ports


class PortsScaffoldTests(unittest.TestCase):
    def test_build_default_ports_returns_all_ports(self) -> None:
        ports = build_default_ports()
        self.assertIsInstance(ports, AppPorts)
        self.assertTrue(hasattr(ports.task, "create_task"))
        self.assertTrue(hasattr(ports.task, "list_open_tasks"))
        self.assertTrue(hasattr(ports.calendar, "create_event"))
        self.assertTrue(hasattr(ports.calendar, "list_events"))
        self.assertTrue(hasattr(ports.storage, "get_state"))
        self.assertTrue(hasattr(ports.storage, "set_state"))


if __name__ == "__main__":
    unittest.main()
