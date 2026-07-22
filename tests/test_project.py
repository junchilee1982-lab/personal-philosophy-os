from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from personal_philosophy_os import __version__
from personal_philosophy_os.validation import validate_vault

ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def test_release_versions_are_aligned(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), __version__)

        expected_plugin_version = "0.1.0-alpha.1"
        for manifest in (
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / ".claude-plugin" / "plugin.json",
        ):
            value = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(value["version"], expected_plugin_version)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"[{expected_plugin_version}]", changelog)

    def test_tracked_synthetic_example_is_valid(self) -> None:
        report = validate_vault(ROOT / "examples" / "synthetic-vault")
        self.assertTrue(report.valid, report.to_dict())

    def test_source_skill_and_wheel_bundle_match(self) -> None:
        public_skill = ROOT / "skills" / "personal-thought-vault"
        bundled_skill = (
            ROOT / "src" / "personal_philosophy_os" / "skill_bundle" / "personal-thought-vault"
        )
        public_files = {
            path.relative_to(public_skill): path.read_bytes()
            for path in public_skill.rglob("*")
            if path.is_file()
        }
        bundled_files = {
            path.relative_to(bundled_skill): path.read_bytes()
            for path in bundled_skill.rglob("*")
            if path.is_file()
        }
        self.assertEqual(public_files, bundled_files)

    def test_skill_validator(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_skill.py"),
                str(ROOT / "skills" / "personal-thought-vault"),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
