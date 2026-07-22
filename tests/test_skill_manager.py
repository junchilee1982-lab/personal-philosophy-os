from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from personal_philosophy_os.errors import InstallError
from personal_philosophy_os.skill_manager import install_skill, uninstall_skill


class SkillManagerTests(unittest.TestCase):
    def test_install_is_repeatable_and_uninstall_is_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installed = install_skill(target="both", home=home)
            self.assertEqual(len(installed), 2)
            self.assertEqual(installed[0], home / ".agents" / "skills" / "personal-thought-vault")
            self.assertEqual(installed[1], home / ".claude" / "skills" / "personal-thought-vault")
            installation_ids = set()
            for target_name, path in zip(("codex", "claude"), installed):
                self.assertTrue((path / "SKILL.md").is_file())
                self.assertTrue((path / ".ppos-managed.json").is_file())
                marker = json.loads((path / ".ppos-managed.json").read_text(encoding="utf-8"))
                self.assertEqual(marker["product"], "personal-philosophy-os")
                self.assertEqual(marker["skill"], "personal-thought-vault")
                self.assertEqual(marker["target"], target_name)
                self.assertEqual(marker["scope"], "user")
                self.assertTrue(marker["installation_id"])
                installation_ids.add(marker["installation_id"])
            self.assertEqual(len(installation_ids), 1)

            second = install_skill(target="both", home=home)
            self.assertEqual(second, installed)
            removed = uninstall_skill(target="both", home=home)
            self.assertEqual(removed, installed)
            self.assertTrue(all(not path.exists() for path in installed))
            self.assertEqual(uninstall_skill(target="both", home=home), [])

    def test_install_refuses_unmanaged_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / ".agents" / "skills" / "personal-thought-vault"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("user-owned", encoding="utf-8")
            with self.assertRaises(InstallError):
                install_skill(target="codex", home=home)
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "user-owned")

    def test_both_preflight_prevents_partial_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex = home / ".agents" / "skills" / "personal-thought-vault"
            claude = home / ".claude" / "skills" / "personal-thought-vault"
            claude.mkdir(parents=True)
            (claude / "SKILL.md").write_text("user-owned", encoding="utf-8")

            with self.assertRaises(InstallError):
                install_skill(target="both", home=home)

            self.assertFalse(codex.exists())
            self.assertEqual((claude / "SKILL.md").read_text(encoding="utf-8"), "user-owned")

    def test_both_rolls_back_when_second_commit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            real_replace = os.replace
            calls = 0

            def fail_second_commit(source: object, destination: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic commit failure")
                real_replace(source, destination)

            with mock.patch(
                "personal_philosophy_os.skill_manager.os.replace",
                side_effect=fail_second_commit,
            ):
                with self.assertRaises(InstallError):
                    install_skill(target="both", home=home)

            self.assertFalse((home / ".agents" / "skills" / "personal-thought-vault").exists())
            self.assertFalse((home / ".claude" / "skills" / "personal-thought-vault").exists())

    def test_uninstall_refuses_unmanaged_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / ".claude" / "skills" / "personal-thought-vault"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("user-owned", encoding="utf-8")
            with self.assertRaises(InstallError):
                uninstall_skill(target="claude", home=home)

    def test_invalid_markers_are_unmanaged_and_never_removed(self) -> None:
        corruptions = {
            "invalid UTF-8": lambda marker: marker.write_bytes(b"\xff"),
            "wrong product": lambda marker: self._change_marker(marker, product="other"),
            "wrong skill": lambda marker: self._change_marker(marker, skill="other"),
            "invalid installation id": lambda marker: self._change_marker(
                marker, installation_id="not-a-uuid"
            ),
            "wrong target": lambda marker: self._change_marker(marker, target="claude"),
            "wrong scope": lambda marker: self._change_marker(marker, scope="project"),
        }
        for name, corrupt in corruptions.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                destination = install_skill(target="codex", home=home)[0]
                marker = destination / ".ppos-managed.json"
                corrupt(marker)
                marker_before = marker.read_bytes()
                skill_before = (destination / "SKILL.md").read_bytes()

                with self.assertRaises(InstallError):
                    uninstall_skill(target="codex", home=home)
                self.assertEqual(marker.read_bytes(), marker_before)
                self.assertEqual((destination / "SKILL.md").read_bytes(), skill_before)

                with self.assertRaises(InstallError):
                    install_skill(target="codex", home=home)
                self.assertEqual(marker.read_bytes(), marker_before)

                self.assertEqual(
                    install_skill(target="codex", home=home, force=True), [destination]
                )
                self.assertEqual(uninstall_skill(target="codex", home=home), [destination])

    def test_both_uninstall_preflight_leaves_first_target_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex = install_skill(target="codex", home=home)[0]
            codex_marker = (codex / ".ppos-managed.json").read_bytes()
            claude = home / ".claude" / "skills" / "personal-thought-vault"
            claude.mkdir(parents=True)
            (claude / "SKILL.md").write_text("user-owned", encoding="utf-8")

            with mock.patch("personal_philosophy_os.skill_manager.os.replace") as replace:
                with self.assertRaises(InstallError):
                    uninstall_skill(target="both", home=home)
                replace.assert_not_called()

            self.assertEqual((codex / ".ppos-managed.json").read_bytes(), codex_marker)
            self.assertEqual((claude / "SKILL.md").read_text(encoding="utf-8"), "user-owned")

    def test_both_uninstall_rolls_back_when_second_rename_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installed = install_skill(target="both", home=home)
            markers_before = [(path / ".ppos-managed.json").read_bytes() for path in installed]
            real_replace = os.replace
            calls = 0

            def fail_second_rename(source: object, destination: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic rename failure")
                real_replace(source, destination)

            with mock.patch(
                "personal_philosophy_os.skill_manager.os.replace",
                side_effect=fail_second_rename,
            ):
                with self.assertRaises(InstallError):
                    uninstall_skill(target="both", home=home)

            for path, marker_before in zip(installed, markers_before):
                self.assertEqual((path / ".ppos-managed.json").read_bytes(), marker_before)
                self.assertEqual(list(path.parent.glob(".personal-thought-vault.uninstall-*")), [])

    @staticmethod
    def _change_marker(marker: Path, **changes: str) -> None:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        payload.update(changes)
        marker.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
