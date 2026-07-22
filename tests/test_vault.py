from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_philosophy_os.errors import AuthorizationError, ConfigurationError
from personal_philosophy_os.io_utils import read_json, read_jsonl, write_json, write_jsonl
from personal_philosophy_os.validation import validate_vault
from personal_philosophy_os.vault import init_vault, open_vault


class VaultTests(unittest.TestCase):
    def test_empty_vault_initializes_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root)
            report = validate_vault(root)
            self.assertTrue(report.valid, report.to_dict())
            self.assertEqual(report.checked_records, 0)

    def test_demo_vault_full_read_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            vault = init_vault(root, demo=True)
            self.assertTrue(validate_vault(root).valid)

            evidence = vault.search("承担的代价", channel="evidence")
            self.assertEqual(evidence[0].record_id, "card-0001")
            conclusions = vault.search("选择", channel="conclusion")
            self.assertEqual(conclusions[0].record_id, "principle-001")

            context = vault.root_context("root-04")
            self.assertEqual(context.root["id"], "root-04")
            self.assertIn("card-0001", {row["id"] for row in context.cards})
            self.assertIn("principle-001", {row["id"] for row in context.principles})

    def test_init_refuses_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            root.mkdir()
            (root / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                init_vault(root)
            self.assertEqual((root / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_mode_change_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = init_vault(Path(directory) / "vault")
            with self.assertRaises(AuthorizationError):
                vault.set_mode("shadow")
            self.assertEqual(vault.mode, "active")
            vault.set_mode("shadow", confirm=True)
            self.assertEqual(vault.mode, "shadow")

    def test_unicode_line_separator_does_not_split_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            record = {"id": "card-1", "text": "left\u2028right", "synthetic": True}
            write_jsonl(path, [record])
            loaded = read_jsonl(path)
            self.assertEqual(loaded, [record])

    def test_unclassified_root_cannot_have_secondary_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            path = root / "mappings" / "root-mappings.jsonl"
            records = read_jsonl(path)
            records[-1]["secondary_roots"] = ["root-01"]
            write_jsonl(path, records)
            report = validate_vault(root)
            self.assertFalse(report.valid)
            self.assertIn("M011", {issue.code for issue in report.issues})

    def test_rejected_mapping_is_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            vault = init_vault(root, demo=True)
            verdict = {
                "schema_version": 1,
                "object_type": "mapping",
                "object_id": "card-0001",
                "object_version": 1,
                "ledger_version": 1,
                "verdict": "rejected",
                "actor_id": "person:self",
                "reason": "synthetic correction",
                "created_at": "2026-01-16",
                "synthetic": True,
            }
            write_jsonl(root / "mappings" / "verdicts.jsonl", [verdict])
            self.assertTrue(validate_vault(root).valid)
            self.assertNotIn("card-0001", vault.effective_mappings())

    def test_only_owner_can_issue_mapping_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            verdict = {
                "schema_version": 1,
                "object_type": "mapping",
                "object_id": "card-0001",
                "object_version": 1,
                "ledger_version": 1,
                "verdict": "rejected",
                "actor_id": "agent:example",
                "reason": "synthetic unauthorized verdict",
                "created_at": "2026-01-16",
                "synthetic": True,
            }
            write_jsonl(root / "mappings" / "verdicts.jsonl", [verdict])
            report = validate_vault(root)
            self.assertFalse(report.valid)
            self.assertIn("D006", {issue.code for issue in report.issues})

    def test_candidate_cannot_follow_confirmed_mapping_even_out_of_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            path = root / "mappings" / "root-mappings.jsonl"
            records = read_jsonl(path)
            first = records[0]
            candidate = dict(first)
            candidate.update(
                {
                    "version": 2,
                    "status": "ai_candidate",
                    "mapped_by": "agent:example",
                    "confirmed_by": None,
                    "created_at": "2026-01-16",
                }
            )
            write_jsonl(path, [candidate, *records])
            report = validate_vault(root)
            self.assertFalse(report.valid)
            self.assertIn("M016", {issue.code for issue in report.issues})

    def test_candidate_context_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            principles_path = root / "principles" / "principles.jsonl"
            rows = read_jsonl(principles_path)
            rows.append(
                {
                    "schema_version": 1,
                    "id": "principle-003",
                    "version": 1,
                    "status": "candidate",
                    "statement": "合成候选原则。",
                    "primary_root": "root-04",
                    "secondary_roots": [],
                    "evidence_card_ids": ["card-0001"],
                    "conditions": "synthetic",
                    "extreme_cost": "synthetic",
                    "opposing_principle_ids": [],
                    "case_ids": [],
                    "confirmed_by": None,
                    "created_at": "2026-01-16",
                    "synthetic": True,
                }
            )
            write_jsonl(principles_path, rows)
            vault = open_vault(root)
            normal_ids = {row["id"] for row in vault.root_context("root-04").principles}
            candidate_ids = {
                row["id"]
                for row in vault.root_context("root-04", include_candidates=True).principles
            }
            self.assertNotIn("principle-003", normal_ids)
            self.assertIn("principle-003", candidate_ids)

    def test_evidence_search_defaults_to_owner_cards_and_reports_subject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            cards_path = root / "cards" / "cards.jsonl"
            cards = read_jsonl(cards_path)
            third_party = dict(cards[0])
            third_party.update(
                {
                    "id": "card-third-party",
                    "subject_id": "person:other",
                    "text": "outsider-only-token",
                }
            )
            write_jsonl(cards_path, [*cards, third_party])

            vault = open_vault(root)
            self.assertEqual(vault.search("outsider-only-token", channel="evidence"), [])
            owner_hit = vault.search("承担的代价", channel="evidence")[0]
            self.assertEqual(owner_hit.subject_id, "person:self")
            self.assertEqual(owner_hit.to_dict()["subject_id"], "person:self")

    def test_confirmed_principle_rejects_third_party_only_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            cards_path = root / "cards" / "cards.jsonl"
            cards = read_jsonl(cards_path)
            third_party = dict(cards[0])
            third_party.update({"id": "card-third-party", "subject_id": "person:other"})
            write_jsonl(cards_path, [*cards, third_party])
            principles_path = root / "principles" / "principles.jsonl"
            principles = read_jsonl(principles_path)
            principles[0]["evidence_card_ids"] = ["card-third-party"]
            write_jsonl(principles_path, principles)

            codes = {issue.code for issue in validate_vault(root).issues}
            self.assertIn("P011", codes)
            self.assertIn("P012", codes)

    def test_case_history_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            cases_path = root / "cases" / "cases.jsonl"
            base = read_jsonl(cases_path)[0]

            duplicate = dict(base)
            write_jsonl(cases_path, [base, duplicate])
            self.assertIn("K005", {issue.code for issue in validate_vault(root).issues})

            gap = dict(base)
            gap.update({"version": 3, "status": "candidate", "confirmed_by": None})
            write_jsonl(cases_path, [base, gap])
            gap_codes = {issue.code for issue in validate_vault(root).issues}
            self.assertIn("K008", gap_codes)
            self.assertIn("K009", gap_codes)

            rejected = dict(base)
            rejected.update({"status": "rejected", "confirmed_by": "agent:example"})
            write_jsonl(cases_path, [rejected])
            self.assertIn("K007", {issue.code for issue in validate_vault(root).issues})

            invalid_status = dict(base)
            invalid_status["status"] = "accepted"
            write_jsonl(cases_path, [invalid_status])
            self.assertIn("K006", {issue.code for issue in validate_vault(root).issues})

    def test_case_unclassified_root_requires_empty_secondary_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            cases_path = root / "cases" / "cases.jsonl"
            cases = read_jsonl(cases_path)
            cases[0].update({"primary_root": "root-00", "secondary_roots": ["root-01"]})
            write_jsonl(cases_path, cases)

            codes = {issue.code for issue in validate_vault(root).issues}
            self.assertIn("K014", codes)

    def test_malformed_collection_types_are_invalid_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)
            config = read_json(root / "vault.json")
            config["rollout_mode"] = []
            write_json(root / "vault.json", config)
            mappings_path = root / "mappings" / "root-mappings.jsonl"
            mappings = read_jsonl(mappings_path)
            mappings[0]["primary_root"] = []
            write_jsonl(mappings_path, mappings)
            cases_path = root / "cases" / "cases.jsonl"
            cases = read_jsonl(cases_path)
            cases[0]["version"] = []
            write_jsonl(cases_path, cases)

            report = validate_vault(root)
            self.assertFalse(report.valid)
            codes = {issue.code for issue in report.issues}
            self.assertTrue({"V014", "M005", "K004"}.issubset(codes))

    def test_reflection_and_external_source_schema_types_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            init_vault(root, demo=True)

            reflections_path = root / "reflections" / "reflections.jsonl"
            reflections = read_jsonl(reflections_path)
            reflections[0]["version"] = []
            reflections[0]["principle_ids"] = ["principle-missing"]
            write_jsonl(reflections_path, reflections)

            sources_path = root / "sources" / "external-sources.jsonl"
            sources = read_jsonl(sources_path)
            sources[0]["version"] = []
            sources[0]["owner_interpretation"] = []
            write_jsonl(sources_path, sources)

            codes = {issue.code for issue in validate_vault(root).issues}
            self.assertTrue({"F001", "F005", "S006", "S008"}.issubset(codes))


if __name__ == "__main__":
    unittest.main()
