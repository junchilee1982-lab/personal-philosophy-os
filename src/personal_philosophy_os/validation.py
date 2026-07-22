"""Dependency-free validation for a Personal Philosophy OS Vault."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .errors import VaultValidationError
from .io_utils import read_json, read_jsonl
from .models import ValidationReport

REQUIRED_JSONL = {
    "cards/cards.jsonl": "cards",
    "mappings/root-mappings.jsonl": "mappings",
    "mappings/verdicts.jsonl": "verdicts",
    "principles/principles.jsonl": "principles",
    "cases/cases.jsonl": "cases",
    "reflections/reflections.jsonl": "reflections",
    "sources/external-sources.jsonl": "external_sources",
}


def validate_vault(vault: str | Path) -> ValidationReport:
    root = Path(vault).expanduser().resolve(strict=False)
    report = ValidationReport(vault=str(root))
    if not root.is_dir():
        report.add("V001", ".", "Vault directory does not exist")
        return report

    config = _load_json(root, "vault.json", report)
    roots_doc = _load_json(root, "roots.json", report)
    datasets: dict[str, list[dict[str, Any]]] = {}
    for relative, key in REQUIRED_JSONL.items():
        datasets[key] = _load_jsonl(root, relative, report)

    if config is None or roots_doc is None:
        return report
    if not isinstance(config, dict):
        report.add("V010", "vault.json", "Vault configuration must be an object")
        return report
    if not isinstance(roots_doc, dict) or not isinstance(roots_doc.get("roots"), list):
        report.add("V011", "roots.json", "Root registry must contain a roots array")
        return report

    owner_id = _nested_string(config, "owner", "id")
    if not owner_id:
        report.add("V012", "vault.json", "owner.id must be a non-empty string")
        owner_id = "person:self"
    if config.get("schema_version") != 1:
        report.add("V013", "vault.json", "unsupported schema_version")
    rollout_mode = config.get("rollout_mode")
    if not _enum_value(rollout_mode, {"stable", "shadow", "active"}):
        report.add("V014", "vault.json", "rollout_mode must be stable, shadow, or active")

    policies = config.get("policies")
    if not isinstance(policies, dict):
        report.add("V015", "vault.json", "policies must be an object")
        policies = {}
    unclassified = policies.get("unclassified_root", "root-00")
    max_secondary = policies.get("max_secondary_roots", 2)
    if not isinstance(unclassified, str) or not unclassified:
        report.add("V016", "vault.json", "unclassified_root must be a string")
        unclassified = "root-00"
    if not isinstance(max_secondary, int) or isinstance(max_secondary, bool) or max_secondary < 0:
        report.add("V017", "vault.json", "max_secondary_roots must be a non-negative integer")
        max_secondary = 2
    root_ids = _validate_roots(roots_doc["roots"], unclassified, report)
    card_index = _validate_cards(datasets["cards"], report)
    card_ids = set(card_index)
    mapping_keys = _validate_mappings(
        datasets["mappings"],
        card_ids,
        root_ids,
        unclassified,
        max_secondary,
        owner_id,
        report,
    )
    _validate_verdicts(datasets["verdicts"], mapping_keys, owner_id, report)
    principle_ids = _validate_principles(
        datasets["principles"],
        card_index,
        root_ids,
        unclassified,
        max_secondary,
        owner_id,
        report,
    )
    case_ids = _validate_cases(
        datasets["cases"],
        principle_ids,
        root_ids,
        unclassified,
        max_secondary,
        owner_id,
        report,
    )
    _validate_principle_links(datasets["principles"], principle_ids, case_ids, report)
    _validate_reflections(datasets["reflections"], principle_ids, owner_id, report)
    _validate_external_sources(
        datasets["external_sources"], principle_ids, root_ids, owner_id, report
    )
    return report


def require_valid_vault(vault: str | Path) -> ValidationReport:
    report = validate_vault(vault)
    if not report.valid:
        summary = "; ".join(f"{issue.code} {issue.path}" for issue in report.issues[:5])
        raise VaultValidationError(f"Vault validation failed: {summary}")
    return report


def _load_json(root: Path, relative: str, report: ValidationReport) -> Any | None:
    path = root / relative
    try:
        value = read_json(path)
    except VaultValidationError as exc:
        report.add("V002", relative, str(exc))
        return None
    report.checked_files += 1
    return value


def _load_jsonl(root: Path, relative: str, report: ValidationReport) -> list[dict[str, Any]]:
    path = root / relative
    try:
        records = read_jsonl(path)
    except VaultValidationError as exc:
        report.add("V003", relative, str(exc))
        return []
    report.checked_files += 1
    report.checked_records += len(records)
    return records


def _validate_roots(roots: list[Any], unclassified: str, report: ValidationReport) -> set[str]:
    seen: set[str] = set()
    unclassified_count = 0
    for index, row in enumerate(roots, start=1):
        path = f"roots.json#roots[{index - 1}]"
        if not isinstance(row, dict):
            report.add("R001", path, "root must be an object")
            continue
        root_id = row.get("id")
        if not _nonempty_string(root_id):
            report.add("R002", path, "root id must be a non-empty string")
            continue
        if root_id in seen:
            report.add("R003", path, "duplicate root id")
        seen.add(root_id)
        if not _nonempty_string(row.get("question_zh")) and not _nonempty_string(
            row.get("question_en")
        ):
            report.add("R004", path, "root needs at least one question label")
        if row.get("unclassified") is True:
            unclassified_count += 1
            if root_id != unclassified:
                report.add("R005", path, "unclassified flag conflicts with policy")
    if unclassified not in seen:
        report.add("R006", "roots.json", "configured unclassified root does not exist")
    if unclassified_count != 1:
        report.add("R007", "roots.json", "exactly one root must be unclassified")
    return seen


def _validate_cards(
    records: list[dict[str, Any]], report: ValidationReport
) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for line, row in enumerate(records, start=1):
        path = "cards/cards.jsonl"
        _validate_schema_version(row, path, line, report)
        card_id = row.get("id")
        if not _nonempty_string(card_id):
            report.add("C001", path, "card id must be a non-empty string", line=line)
            continue
        if card_id in seen:
            report.add("C002", path, "duplicate card id", line=line)
        else:
            seen[card_id] = row
        _require_strings(row, ("kind", "subject_id", "text", "evidence_grade"), path, line, report)
        if not _enum_value(row.get("status"), {"candidate", "confirmed", "rejected"}):
            report.add("C003", path, "invalid card status", line=line)
        _validate_date(row.get("created_at"), path, line, report)
        if not isinstance(row.get("synthetic"), bool):
            report.add("C004", path, "synthetic must be boolean", line=line)
    return seen


def _validate_mappings(
    records: list[dict[str, Any]],
    card_ids: set[str],
    root_ids: set[str],
    unclassified: str,
    max_secondary: int,
    owner_id: str,
    report: ValidationReport,
) -> set[tuple[str, int]]:
    path = "mappings/root-mappings.jsonl"
    versions: dict[str, list[int]] = defaultdict(list)
    keys: set[tuple[str, int]] = set()
    rows_by_card: dict[str, list[tuple[int, str, int]]] = defaultdict(list)
    for line, row in enumerate(records, start=1):
        _validate_record_common(row, path, line, report)
        card_id = row.get("card_id")
        version = row.get("version")
        if not _nonempty_string(card_id):
            report.add("M001", path, "card_id must be a non-empty string", line=line)
            continue
        if card_id not in card_ids:
            report.add("M002", path, "mapping references an unknown card", line=line)
        if not _positive_int(version):
            report.add("M003", path, "version must be a positive integer", line=line)
            continue
        key = (card_id, version)
        if key in keys:
            report.add("M004", path, "duplicate card_id and version", line=line)
        keys.add(key)
        versions[card_id].append(version)
        rows_by_card[card_id].append((version, str(row.get("status")), line))

        primary = row.get("primary_root")
        secondary = row.get("secondary_roots")
        candidates = row.get("candidate_roots", [])
        primary_valid = _nonempty_string(primary)
        if not primary_valid or primary not in root_ids:
            report.add("M005", path, "primary_root is not registered", line=line)
        if not _string_list(secondary):
            report.add("M006", path, "secondary_roots must be a string list", line=line)
            secondary = []
        if not _string_list(candidates):
            report.add("M007", path, "candidate_roots must be a string list", line=line)
            candidates = []
        if (
            len(secondary) > max_secondary
            or len(set(secondary)) != len(secondary)
            or len(set(candidates)) != len(candidates)
        ):
            report.add("M008", path, "secondary root count or uniqueness is invalid", line=line)
        if primary in secondary or unclassified in secondary:
            report.add("M009", path, "secondary roots contain a forbidden root", line=line)
        if any(item not in root_ids for item in secondary + candidates):
            report.add("M010", path, "mapping references an unknown root", line=line)
        if primary == unclassified and secondary:
            report.add(
                "M011", path, "unclassified primary requires empty secondary roots", line=line
            )
        if primary != unclassified and candidates:
            report.add(
                "M012", path, "candidate_roots are only valid for unclassified primary", line=line
            )

        status = row.get("status")
        if not _enum_value(status, {"ai_candidate", "confirmed"}):
            report.add("M013", path, "invalid mapping status", line=line)
        if not _nonempty_string(row.get("mapped_by")) or not _nonempty_string(row.get("reason")):
            report.add("M014", path, "mapped_by and reason must be non-empty strings", line=line)
        if not _optional_string(row.get("confirmed_by")):
            report.add("M018", path, "confirmed_by must be a string or null", line=line)
        if status == "confirmed":
            if row.get("confirmed_by") != owner_id:
                report.add("M015", path, "confirmed mapping must name the owner", line=line)
        _validate_date(row.get("created_at"), path, line, report)

    for card_id, values in versions.items():
        ordered = sorted(values)
        if ordered != list(range(1, max(ordered) + 1)):
            report.add("M017", path, f"mapping version chain is not continuous for {card_id}")
    for card_id, rows in rows_by_card.items():
        confirmed_versions = [version for version, status, _ in rows if status == "confirmed"]
        if not confirmed_versions:
            continue
        first_confirmed = min(confirmed_versions)
        for version, status, line in rows:
            if status == "ai_candidate" and version > first_confirmed:
                report.add(
                    "M016",
                    path,
                    "AI candidate cannot follow a confirmed mapping version",
                    line=line,
                )
    return keys


def _validate_verdicts(
    records: list[dict[str, Any]],
    mapping_keys: set[tuple[str, int]],
    owner_id: str,
    report: ValidationReport,
) -> None:
    path = "mappings/verdicts.jsonl"
    keys: set[tuple[str, int, int]] = set()
    chains: dict[tuple[str, int], list[int]] = defaultdict(list)
    for line, row in enumerate(records, start=1):
        if row.get("object_type") != "mapping":
            report.add("D001", path, "object_type must be mapping", line=line)
        object_id = row.get("object_id")
        object_version = row.get("object_version")
        ledger_version = row.get("ledger_version")
        if not _positive_int(object_version) or not _positive_int(ledger_version):
            report.add("D003", path, "verdict versions must be positive integers", line=line)
            continue
        if (str(object_id), object_version) not in mapping_keys:
            report.add("D002", path, "verdict references an unknown mapping version", line=line)
        key = (str(object_id), object_version, ledger_version)
        if key in keys:
            report.add("D004", path, "duplicate verdict key", line=line)
        keys.add(key)
        chains[(str(object_id), object_version)].append(ledger_version)
        if not _enum_value(row.get("verdict"), {"rejected", "withdrawn"}):
            report.add("D005", path, "invalid verdict", line=line)
        if row.get("actor_id") != owner_id:
            report.add("D006", path, "only the owner may issue a verdict", line=line)
        _validate_date(row.get("created_at"), path, line, report)
    for target, versions in chains.items():
        ordered = sorted(versions)
        if ordered != list(range(1, max(ordered) + 1)):
            report.add("D007", path, f"verdict ledger chain is not continuous for {target}")


def _validate_principles(
    records: list[dict[str, Any]],
    card_index: dict[str, dict[str, Any]],
    root_ids: set[str],
    unclassified: str,
    max_secondary: int,
    owner_id: str,
    report: ValidationReport,
) -> set[str]:
    path = "principles/principles.jsonl"
    ids: set[str] = set()
    keys: set[tuple[str, int]] = set()
    versions: dict[str, list[int]] = defaultdict(list)
    rows_by_id: dict[str, list[tuple[int, str, int]]] = defaultdict(list)
    for line, row in enumerate(records, start=1):
        _validate_record_common(row, path, line, report)
        principle_id = row.get("id")
        version = row.get("version")
        if not _nonempty_string(principle_id) or not _positive_int(version):
            report.add("P001", path, "principle id and version are required", line=line)
            continue
        key = (principle_id, version)
        if key in keys:
            report.add("P002", path, "duplicate principle id and version", line=line)
        keys.add(key)
        ids.add(principle_id)
        versions[principle_id].append(version)
        rows_by_id[principle_id].append((version, str(row.get("status")), line))
        _require_strings(row, ("statement", "conditions", "extreme_cost"), path, line, report)
        status = row.get("status")
        if not _enum_value(status, {"candidate", "confirmed", "rejected"}):
            report.add("P003", path, "invalid principle status", line=line)
        primary = row.get("primary_root")
        if not _nonempty_string(primary) or primary not in root_ids:
            report.add("P004", path, "unknown primary root", line=line)
        secondary = row.get("secondary_roots")
        secondary_valid = _string_list(secondary)
        if (
            not secondary_valid
            or len(secondary) > max_secondary
            or len(set(secondary)) != len(secondary)
        ):
            report.add("P005", path, "invalid secondary roots", line=line)
            secondary = []
        if any(item not in root_ids for item in secondary):
            report.add("P013", path, "secondary roots contain an unknown root", line=line)
        if primary in secondary or unclassified in secondary:
            report.add("P014", path, "secondary roots contain a forbidden root", line=line)
        if primary == unclassified and secondary:
            report.add(
                "P015", path, "unclassified primary requires empty secondary roots", line=line
            )
        evidence = row.get("evidence_card_ids")
        evidence_valid = _string_list(evidence)
        if (
            not evidence_valid
            or len(set(evidence)) != len(evidence)
            or any(item not in card_index for item in evidence)
        ):
            report.add("P006", path, "invalid evidence card references", line=line)
            evidence = []
        referenced_cards = [card_index[item] for item in evidence if item in card_index]
        if any(card.get("subject_id") != owner_id for card in referenced_cards):
            report.add(
                "P011", path, "third-party cards cannot support a personal principle", line=line
            )
        if status == "confirmed" and not any(
            card.get("subject_id") == owner_id and card.get("status") == "confirmed"
            for card in referenced_cards
        ):
            report.add(
                "P012",
                path,
                "confirmed principle needs confirmed evidence from the owner",
                line=line,
            )
        if not _unique_string_list(row.get("opposing_principle_ids")):
            report.add("P016", path, "invalid opposing principle references", line=line)
        if not _unique_string_list(row.get("case_ids")):
            report.add("P017", path, "invalid case references", line=line)
        if not _optional_string(row.get("confirmed_by")):
            report.add("P018", path, "confirmed_by must be a string or null", line=line)
        if status == "confirmed" and row.get("confirmed_by") != owner_id:
            report.add("P007", path, "confirmed principle must name the owner", line=line)
        if status == "rejected" and row.get("confirmed_by") != owner_id:
            report.add("P008", path, "rejected principle must name the owner", line=line)
        _validate_date(row.get("created_at"), path, line, report)
    for principle_id, values in versions.items():
        ordered = sorted(values)
        if ordered != list(range(1, max(ordered) + 1)):
            report.add(
                "P009", path, f"principle version chain is not continuous for {principle_id}"
            )
    for principle_id, rows in rows_by_id.items():
        human_versions = [
            version for version, status, _ in rows if status in {"confirmed", "rejected"}
        ]
        if not human_versions:
            continue
        first_human = min(human_versions)
        for version, status, line in rows:
            if status == "candidate" and version > first_human:
                report.add(
                    "P010",
                    path,
                    "AI candidate cannot follow a human principle verdict",
                    line=line,
                )
    return ids


def _validate_principle_links(
    records: list[dict[str, Any]],
    principle_ids: set[str],
    case_ids: set[str],
    report: ValidationReport,
) -> None:
    path = "principles/principles.jsonl"
    for line, row in enumerate(records, start=1):
        opposing = row.get("opposing_principle_ids")
        if _unique_string_list(opposing) and any(item not in principle_ids for item in opposing):
            report.add("P019", path, "unknown opposing principle reference", line=line)
        cases = row.get("case_ids")
        if _unique_string_list(cases) and any(item not in case_ids for item in cases):
            report.add("P020", path, "unknown case reference", line=line)


def _validate_cases(
    records: list[dict[str, Any]],
    principle_ids: set[str],
    root_ids: set[str],
    unclassified: str,
    max_secondary: int,
    owner_id: str,
    report: ValidationReport,
) -> set[str]:
    path = "cases/cases.jsonl"
    ids: set[str] = set()
    keys: set[tuple[str, int]] = set()
    versions: dict[str, list[int]] = defaultdict(list)
    rows_by_id: dict[str, list[tuple[int, str, int]]] = defaultdict(list)
    for line, row in enumerate(records, start=1):
        _validate_record_common(row, path, line, report)
        case_id = row.get("id")
        version = row.get("version")
        valid_key = _nonempty_string(case_id) and _positive_int(version)
        if not valid_key:
            report.add("K004", path, "case id and version are required", line=line)
        else:
            key = (case_id, version)
            if key in keys:
                report.add("K005", path, "duplicate case id and version", line=line)
            keys.add(key)
            ids.add(case_id)
            versions[case_id].append(version)
            rows_by_id[case_id].append((version, str(row.get("status")), line))
        _require_strings(
            row,
            (
                "fact_summary",
                "responsibility",
                "boundary",
                "motivation",
                "cost",
                "action",
                "result",
                "transfer_signal",
                "failure_condition",
            ),
            path,
            line,
            report,
        )
        status = row.get("status")
        if not _enum_value(status, {"candidate", "confirmed", "rejected"}):
            report.add("K006", path, "invalid case status", line=line)
        if not _string_list(row.get("subject_ids")):
            report.add("K010", path, "subject_ids must be a string list", line=line)
        primary = row.get("primary_root")
        if not _nonempty_string(primary) or primary not in root_ids:
            report.add("K001", path, "case references an unknown root", line=line)
        secondary = row.get("secondary_roots")
        if (
            not _string_list(secondary)
            or len(secondary) > max_secondary
            or len(set(secondary)) != len(secondary)
        ):
            report.add("K011", path, "invalid secondary roots", line=line)
            secondary = []
        if any(item not in root_ids for item in secondary):
            report.add("K012", path, "case references an unknown secondary root", line=line)
        if primary in secondary or unclassified in secondary:
            report.add("K013", path, "secondary roots contain a forbidden root", line=line)
        if primary == unclassified and secondary:
            report.add(
                "K014", path, "unclassified primary requires empty secondary roots", line=line
            )
        if not _string_list(row.get("principle_ids")) or any(
            item not in principle_ids for item in row.get("principle_ids", [])
        ):
            report.add("K002", path, "case has invalid principle references", line=line)
        if not _optional_string(row.get("confirmed_by")):
            report.add("K015", path, "confirmed_by must be a string or null", line=line)
        if status == "confirmed" and row.get("confirmed_by") != owner_id:
            report.add("K003", path, "confirmed case must name the owner", line=line)
        if status == "rejected" and row.get("confirmed_by") != owner_id:
            report.add("K007", path, "rejected case must name the owner", line=line)
        _validate_date(row.get("created_at"), path, line, report)

    for case_id, values in versions.items():
        ordered = sorted(values)
        if ordered != list(range(1, max(ordered) + 1)):
            report.add("K008", path, f"case version chain is not continuous for {case_id}")
    for case_id, rows in rows_by_id.items():
        human_versions = [
            version for version, status, _ in rows if status in {"confirmed", "rejected"}
        ]
        if not human_versions:
            continue
        first_human = min(human_versions)
        for version, status, line in rows:
            if status == "candidate" and version > first_human:
                report.add(
                    "K009",
                    path,
                    "AI candidate cannot follow a human case verdict",
                    line=line,
                )
    return ids


def _validate_external_sources(
    records: list[dict[str, Any]],
    principle_ids: set[str],
    root_ids: set[str],
    owner_id: str,
    report: ValidationReport,
) -> None:
    path = "sources/external-sources.jsonl"
    keys: set[tuple[str, int]] = set()
    versions: dict[str, list[int]] = defaultdict(list)
    for line, row in enumerate(records, start=1):
        _validate_record_common(row, path, line, report)
        source_id = row.get("id")
        version = row.get("version")
        if not _nonempty_string(source_id) or not _positive_int(version):
            report.add("S006", path, "source id and version are required", line=line)
        else:
            key = (source_id, version)
            if key in keys:
                report.add("S007", path, "duplicate source id and version", line=line)
            keys.add(key)
            versions[source_id].append(version)
        _require_strings(
            row,
            ("id", "source", "source_text"),
            path,
            line,
            report,
        )
        for field in ("agent_interpretation", "owner_interpretation"):
            if not isinstance(row.get(field), str):
                report.add("S008", path, f"{field} must be a string", line=line)
        relationship = row.get("relationship")
        if not _enum_value(relationship, {"support", "challenge", "tool", "unverified"}):
            report.add("S001", path, "invalid external relationship", line=line)
        status = row.get("status")
        if not _enum_value(status, {"candidate", "accepted", "rejected"}):
            report.add("S002", path, "invalid external source status", line=line)
        if status in ("accepted", "rejected") and row.get("confirmed_by") != owner_id:
            report.add("S003", path, "external verdict must name the owner", line=line)
        if not _optional_string(row.get("confirmed_by")):
            report.add("S009", path, "confirmed_by must be a string or null", line=line)
        if not _string_list(row.get("root_ids")) or any(
            item not in root_ids for item in row.get("root_ids", [])
        ):
            report.add("S004", path, "invalid root references", line=line)
        if not _string_list(row.get("principle_ids")) or any(
            item not in principle_ids for item in row.get("principle_ids", [])
        ):
            report.add("S005", path, "invalid principle references", line=line)
        _validate_date(row.get("created_at"), path, line, report)
    for source_id, values in versions.items():
        ordered = sorted(values)
        if ordered != list(range(1, max(ordered) + 1)):
            report.add("S010", path, f"source version chain is not continuous for {source_id}")


def _validate_reflections(
    records: list[dict[str, Any]],
    principle_ids: set[str],
    owner_id: str,
    report: ValidationReport,
) -> None:
    path = "reflections/reflections.jsonl"
    keys: set[tuple[str, int]] = set()
    versions: dict[str, list[int]] = defaultdict(list)
    for line, row in enumerate(records, start=1):
        _validate_record_common(row, path, line, report)
        reflection_id = row.get("id")
        version = row.get("version")
        if not _nonempty_string(reflection_id) or not _positive_int(version):
            report.add("F001", path, "reflection id and version are required", line=line)
        else:
            key = (reflection_id, version)
            if key in keys:
                report.add("F002", path, "duplicate reflection id and version", line=line)
            keys.add(key)
            versions[reflection_id].append(version)
        for field in (
            "facts_known_then",
            "judgment_then",
            "action",
            "expected_result",
            "actual_result",
            "what_held",
            "what_distorted",
            "revision_proposal",
        ):
            if not isinstance(row.get(field), str):
                report.add("F003", path, f"{field} must be a string", line=line)
        status = row.get("status")
        if not _enum_value(status, {"candidate", "confirmed", "rejected"}):
            report.add("F004", path, "invalid reflection status", line=line)
        if not _string_list(row.get("principle_ids")) or any(
            item not in principle_ids for item in row.get("principle_ids", [])
        ):
            report.add("F005", path, "invalid principle references", line=line)
        if not _optional_string(row.get("confirmed_by")):
            report.add("F006", path, "confirmed_by must be a string or null", line=line)
        if status in {"confirmed", "rejected"} and row.get("confirmed_by") != owner_id:
            report.add("F007", path, "reflection verdict must name the owner", line=line)
        _validate_date(row.get("created_at"), path, line, report)
    for reflection_id, values in versions.items():
        ordered = sorted(values)
        if ordered != list(range(1, max(ordered) + 1)):
            report.add(
                "F008", path, f"reflection version chain is not continuous for {reflection_id}"
            )


def _require_strings(
    row: dict[str, Any],
    fields: tuple[str, ...],
    path: str,
    line: int,
    report: ValidationReport,
) -> None:
    for field in fields:
        if not _nonempty_string(row.get(field)):
            report.add("T001", path, f"{field} must be a non-empty string", line=line)


def _validate_schema_version(
    row: dict[str, Any], path: str, line: int, report: ValidationReport
) -> None:
    value = row.get("schema_version")
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        report.add("T004", path, "unsupported schema_version", line=line)


def _validate_record_common(
    row: dict[str, Any], path: str, line: int, report: ValidationReport
) -> None:
    _validate_schema_version(row, path, line, report)
    if not isinstance(row.get("synthetic"), bool):
        report.add("T005", path, "synthetic must be boolean", line=line)


def _validate_date(value: Any, path: str, line: int, report: ValidationReport) -> None:
    if not isinstance(value, str):
        report.add("T002", path, "date must be an ISO date string", line=line)
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        report.add("T003", path, "date is not a real ISO date", line=line)


def _nested_string(value: Any, parent: str, child: str) -> str | None:
    if not isinstance(value, dict):
        return None
    nested = value.get(parent)
    if not isinstance(nested, dict):
        return None
    result = nested.get(child)
    return result if _nonempty_string(result) else None


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def _unique_string_list(value: Any) -> bool:
    return _string_list(value) and len(set(value)) == len(value)


def _optional_string(value: Any) -> bool:
    return value is None or isinstance(value, str)


def _enum_value(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
