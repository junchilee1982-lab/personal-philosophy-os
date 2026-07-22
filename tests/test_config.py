from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_philosophy_os.config import resolve_vault_path
from personal_philosophy_os.io_utils import write_json


class ConfigTests(unittest.TestCase):
    def test_resolution_priority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config_file = base / "config.json"
            write_json(config_file, {"schema_version": 1, "default_vault": str(base / "config")})
            env = {
                "PPOS_VAULT": str(base / "env"),
                "PERSONAL_THOUGHT_VAULT_HOME": str(base / "alias"),
            }
            self.assertEqual(
                resolve_vault_path(base / "flag", env=env, config_file=config_file),
                (base / "flag").resolve(),
            )
            self.assertEqual(
                resolve_vault_path(env=env, config_file=config_file), (base / "env").resolve()
            )
            self.assertEqual(
                resolve_vault_path(
                    env={"PERSONAL_THOUGHT_VAULT_HOME": str(base / "alias")},
                    config_file=config_file,
                ),
                (base / "alias").resolve(),
            )
            self.assertEqual(
                resolve_vault_path(env={}, config_file=config_file), (base / "config").resolve()
            )

    def test_default_path_uses_supplied_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            resolved = resolve_vault_path(env={}, config_file=home / "missing.json", home=home)
            self.assertTrue(str(resolved).startswith(str(home.resolve())))


if __name__ == "__main__":
    unittest.main()
