from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from config.runtime_env import build_env_from_template, ensure_runtime_env_file


class RuntimeEnvTests(unittest.TestCase):
    def test_build_env_from_template_generates_api_token(self) -> None:
        content = build_env_from_template(
            "APP_VERSION=0.6.0\nVASYA_API_AUTH_TOKEN=\nVASYA_API_REQUIRE_AUTH=true\n",
            token_factory=lambda: "generated-token",
        )

        self.assertIn("APP_VERSION=0.6.0", content)
        self.assertIn("VASYA_API_AUTH_TOKEN=generated-token", content)
        self.assertTrue(content.endswith("\n"))

    def test_ensure_runtime_env_file_creates_default_env_with_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = ensure_runtime_env_file(root, token_factory=lambda: "generated-token")

            self.assertEqual(result.status, "OK")
            self.assertIn("created .env", result.message)
            self.assertIn("VASYA_API_AUTH_TOKEN=generated-token", (root / ".env").read_text(encoding="utf-8"))

    def test_ensure_runtime_env_file_preserves_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_path = root / ".env"
            env_path.write_text("EXISTING=true\n", encoding="utf-8")

            result = ensure_runtime_env_file(root, token_factory=lambda: "generated-token")

            self.assertEqual(result.status, "OK")
            self.assertEqual(env_path.read_text(encoding="utf-8"), "EXISTING=true\n")


if __name__ == "__main__":
    unittest.main()
