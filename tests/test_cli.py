from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from personal_philosophy_os.cli import main


class CliTests(unittest.TestCase):
    def test_cli_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            self.assertEqual(main(["init", "--vault", str(vault), "--demo"]), 0)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["validate", "--vault", str(vault), "--json"])
            self.assertEqual(code, 0)
            validation_text = stdout.getvalue()
            validation = json.loads(validation_text)
            self.assertTrue(validation["valid"])
            self.assertEqual(validation["vault"], "<configured-vault>")
            self.assertNotIn(str(vault.resolve()), validation_text)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "search",
                        "代价",
                        "--vault",
                        str(vault),
                        "--channel",
                        "evidence",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertGreater(len(json.loads(stdout.getvalue())["hits"]), 0)

    def test_mode_set_without_confirm_returns_five(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            main(["init", "--vault", str(vault)])
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["mode", "set", "shadow", "--vault", str(vault)])
            self.assertEqual(code, 5)
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_validate_json_redacts_vault_path_from_file_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            main(["init", "--vault", str(vault)])
            (vault / "vault.json").write_text("{", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["validate", "--vault", str(vault), "--json"])

            output = stdout.getvalue()
            result = json.loads(output)
            self.assertEqual(code, 3)
            self.assertFalse(result["valid"])
            self.assertEqual(result["vault"], "<configured-vault>")
            self.assertEqual(result["issues"][0]["path"], "vault.json")
            self.assertNotIn(str(vault.resolve()), output)
            self.assertNotIn("Traceback", output + stderr.getvalue())

    def test_validate_json_structures_unexpected_bad_data_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            main(["init", "--vault", str(vault)])
            config_path = vault / "vault.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["rollout_mode"] = []
            config_path.write_text(json.dumps(config), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["validate", "--vault", str(vault), "--json"])

            output = stdout.getvalue()
            result = json.loads(output)
            self.assertEqual(code, 3)
            self.assertFalse(result["valid"])
            self.assertEqual(result["issues"][0]["code"], "V014")
            self.assertFalse(Path(result["issues"][0]["path"]).is_absolute())
            self.assertNotIn(str(vault.resolve()), output)
            self.assertNotIn("Traceback", output + stderr.getvalue())

    def test_doctor_json_redacts_vault_path_and_structures_bad_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            main(["init", "--vault", str(vault)])
            (vault / "vault.json").write_text("{", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["doctor", "--vault", str(vault), "--json"])

            output = stdout.getvalue()
            result = json.loads(output)
            self.assertEqual(code, 3)
            self.assertFalse(result["vault_valid"])
            self.assertFalse(Path(result["issues"][0]["path"]).is_absolute())
            self.assertNotIn(str(vault.resolve()), output)
            self.assertNotIn("Traceback", output + stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
