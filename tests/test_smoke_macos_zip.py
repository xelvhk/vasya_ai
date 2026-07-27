from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.smoke_macos_zip import MacOSZipSmokeConfig, validate_zip_artifact


class SmokeMacOSZipTests(unittest.TestCase):
    def test_validate_zip_artifact_accepts_expected_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSZipSmokeConfig(root_dir=Path(tmp))
            _write_zip(
                config,
                [
                    "Vasya AI.app/",
                    "Vasya AI.app/Contents/MacOS/Vasya AI",
                    "Vasya AI.app/Contents/Info.plist",
                    "Vasya AI.app/Contents/Resources/assets/",
                    "Vasya AI Doctor/",
                    "Vasya AI Doctor/Vasya AI Doctor",
                    "Vasya AI Doctor/_internal/dateparser/",
                ],
            )

            checks = validate_zip_artifact(config)

        self.assertTrue(all(check.state == "OK" for check in checks))

    def test_validate_zip_artifact_reports_missing_doctor_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSZipSmokeConfig(root_dir=Path(tmp))
            _write_zip(
                config,
                [
                    "Vasya AI.app/",
                    "Vasya AI.app/Contents/MacOS/Vasya AI",
                    "Vasya AI.app/Contents/Info.plist",
                    "Vasya AI.app/Contents/Resources/assets/",
                ],
            )

            checks = validate_zip_artifact(config)

        failures = {check.name for check in checks if check.state == "FAIL"}
        self.assertIn("doctor companion", failures)
        self.assertIn("doctor executable", failures)

    def test_validate_zip_artifact_rejects_staging_payload_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSZipSmokeConfig(root_dir=Path(tmp))
            _write_zip(
                config,
                [
                    "payload/Vasya AI.app/",
                    "Vasya AI.app/",
                    "Vasya AI.app/Contents/MacOS/Vasya AI",
                    "Vasya AI.app/Contents/Info.plist",
                    "Vasya AI.app/Contents/Resources/assets/",
                    "Vasya AI Doctor/",
                    "Vasya AI Doctor/Vasya AI Doctor",
                    "Vasya AI Doctor/_internal/dateparser/",
                ],
            )

            checks = validate_zip_artifact(config)

        failures = {check.name for check in checks if check.state == "FAIL"}
        self.assertIn("staging wrapper", failures)

    def test_validate_zip_artifact_reports_missing_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MacOSZipSmokeConfig(root_dir=Path(tmp))

            checks = validate_zip_artifact(config)

        self.assertEqual(checks[0].state, "FAIL")
        self.assertIn("missing file", checks[0].message)


def _write_zip(config: MacOSZipSmokeConfig, names: list[str]) -> None:
    config.artifact_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(config.artifact_path, "w") as archive:
        for name in names:
            archive.writestr(name, "")


if __name__ == "__main__":
    unittest.main()
