from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import setup_macos


class SetupMacOSTests(unittest.TestCase):
    def test_build_env_from_example_generates_api_token(self) -> None:
        content = setup_macos._build_env_from_example(
            "APP_VERSION=0.5.50\nVASYA_API_AUTH_TOKEN=\nVASYA_API_REQUIRE_AUTH=true\n"
        )
        self.assertIn("APP_VERSION=0.5.50", content)
        token_line = next(line for line in content.splitlines() if line.startswith("VASYA_API_AUTH_TOKEN="))
        self.assertGreater(len(token_line.split("=", maxsplit=1)[1]), 20)

    def test_existing_env_file_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_path = root / ".env"
            env_path.write_text("EXISTING=true\n", encoding="utf-8")

            result = setup_macos._ensure_env_file(root, dry_run=False)

            self.assertEqual(result.status, "OK")
            self.assertEqual(env_path.read_text(encoding="utf-8"), "EXISTING=true\n")

    def test_run_setup_dry_run_does_not_create_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text("VASYA_API_AUTH_TOKEN=\n", encoding="utf-8")

            results = setup_macos.run_setup(
                root_dir=root,
                dry_run=True,
                install_dependencies=False,
                pull_model=False,
            )

            self.assertFalse((root / ".env").exists())
            self.assertFalse((root / ".venv").exists())
            self.assertTrue(any(result.status == "PLAN" for result in results))

    def test_run_setup_creates_env_and_storage_dirs_without_dependency_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text("VASYA_API_AUTH_TOKEN=\n", encoding="utf-8")

            with patch("scripts.setup_macos.shutil.which", return_value=None):
                results = setup_macos.run_setup(
                    root_dir=root,
                    dry_run=False,
                    install_dependencies=False,
                    pull_model=False,
                )

            self.assertTrue((root / ".env").exists())
            self.assertTrue((root / "storage" / "memory_wiki").is_dir())
            self.assertTrue(any(result.name == "ollama" and result.status == "WARN" for result in results))

    def test_first_run_checklist_mentions_core_commands(self) -> None:
        checklist = "\n".join(setup_macos.first_run_checklist())
        self.assertIn("source .venv/bin/activate", checklist)
        self.assertIn("python scripts/doctor.py", checklist)
        self.assertIn("python main.py", checklist)


if __name__ == "__main__":
    unittest.main()
