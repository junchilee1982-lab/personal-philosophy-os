"""Vault initialization, retrieval and root-context assembly."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import resolve_vault_path
from .defaults import DEFAULT_ROOTS, default_vault_config, demo_records
from .errors import AuthorizationError, ConfigurationError, VaultValidationError
from .io_utils import read_json, read_jsonl, write_json, write_jsonl
from .models import RootContext, SearchHit
from .validation import require_valid_vault

DATA_FILES = {
    "cards": "cards/cards.jsonl",
    "mappings": "mappings/root-mappings.jsonl",
    "verdicts": "mappings/verdicts.jsonl",
    "principles": "principles/principles.jsonl",
    "cases": "cases/cases.jsonl",
    "reflections": "reflections/reflections.jsonl",
    "external_sources": "sources/external-sources.jsonl",
}


def init_vault(path: str | Path, *, demo: bool = False) -> "Vault":
    root = Path(path).expanduser().resolve(strict=False)
    if root.exists() and not root.is_dir():
        raise ConfigurationError("Vault path exists and is not a directory")
    if root.exists() and any(root.iterdir()):
        raise ConfigurationError("Vault directory is not empty; refusing to overwrite")
    root.mkdir(parents=True, exist_ok=True)

    for directory in ("cards", "mappings", "principles", "cases", "reflections", "sources"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    write_json(root / "vault.json", default_vault_config())
    write_json(root / "roots.json", {"schema_version": 1, "roots": DEFAULT_ROOTS})
    records = demo_records() if demo else {key: [] for key in DATA_FILES}
    for key, relative in DATA_FILES.items():
        write_jsonl(root / relative, records[key])
    return open_vault(root)


def open_vault(path: str | Path | None = None, *, validate: bool = True) -> "Vault":
    resolved = resolve_vault_path(path)
    if validate:
        require_valid_vault(resolved)
    return Vault(resolved)


class Vault:
    """Read-oriented interface over a validated local Vault."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve(strict=False)

    @property
    def config(self) -> dict[str, Any]:
        value = read_json(self.root / "vault.json")
        if not isinstance(value, dict):
            raise VaultValidationError("vault.json must contain an object")
        return value

    @property
    def mode(self) -> str:
        return str(self.config.get("rollout_mode", "stable"))

    def set_mode(self, mode: str, *, confirm: bool = False) -> None:
        if mode not in {"stable", "shadow", "active"}:
            raise ConfigurationError("mode must be stable, shadow, or active")
        if not confirm:
            raise AuthorizationError("mode changes require explicit confirmation")
        config = self.config
        config["rollout_mode"] = mode
        write_json(self.root / "vault.json", config)

    def search(
        self,
        query: str,
        *,
        channel: str = "evidence",
        top_k: int = 5,
    ) -> list[SearchHit]:
        if channel not in {"evidence", "conclusion"}:
            raise ConfigurationError("channel must be evidence or conclusion")
        if not query.strip():
            raise ConfigurationError("query cannot be empty")
        if top_k < 1 or top_k > 100:
            raise ConfigurationError("top_k must be between 1 and 100")

        mappings = self.effective_mappings(include_candidates=False)
        roots_by_card = {
            card_id: tuple([row["primary_root"], *row.get("secondary_roots", [])])
            for card_id, row in mappings.items()
        }
        owner = self.config.get("owner")
        owner_id = owner.get("id") if isinstance(owner, dict) else None
        hits: list[SearchHit] = []
        if channel == "evidence":
            for row in self._records("cards"):
                if row.get("status") != "confirmed" or row.get("subject_id") != owner_id:
                    continue
                score = _score(query, str(row.get("text", "")))
                if score <= 0:
                    continue
                hits.append(
                    SearchHit(
                        kind="card",
                        record_id=str(row["id"]),
                        text=str(row["text"]),
                        score=score,
                        status=str(row["status"]),
                        subject_id=str(row["subject_id"]),
                        root_ids=roots_by_card.get(str(row["id"]), ()),
                    )
                )
        else:
            for row in _effective_versions(self._records("principles")):
                if row.get("status") != "confirmed":
                    continue
                score = _score(query, str(row.get("statement", "")))
                if score <= 0:
                    continue
                hits.append(
                    SearchHit(
                        kind="principle",
                        record_id=str(row["id"]),
                        text=str(row["statement"]),
                        score=score,
                        status=str(row["status"]),
                        subject_id=str(owner_id) if owner_id is not None else None,
                        root_ids=tuple([row["primary_root"], *row.get("secondary_roots", [])]),
                        evidence_ids=tuple(row.get("evidence_card_ids", [])),
                    )
                )
        return sorted(hits, key=lambda hit: (-hit.score, hit.record_id))[:top_k]

    def effective_mappings(self, *, include_candidates: bool = False) -> dict[str, dict[str, Any]]:
        mappings = self._records("mappings")
        rejected = _rejected_mapping_keys(self._records("verdicts"))
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in mappings:
            key = (str(row.get("card_id")), int(row.get("version", 0)))
            if key not in rejected:
                grouped[key[0]].append(row)

        selected: dict[str, dict[str, Any]] = {}
        for card_id, rows in grouped.items():
            confirmed = [row for row in rows if row.get("status") == "confirmed"]
            if confirmed:
                selected[card_id] = max(confirmed, key=lambda row: int(row["version"]))
                continue
            if include_candidates:
                candidates = [row for row in rows if row.get("status") == "ai_candidate"]
                if candidates:
                    selected[card_id] = max(candidates, key=lambda row: int(row["version"]))
        return selected

    def root_context(self, root_id: str, *, include_candidates: bool = False) -> RootContext:
        roots_doc = read_json(self.root / "roots.json")
        roots = roots_doc.get("roots", []) if isinstance(roots_doc, dict) else []
        root = next((row for row in roots if row.get("id") == root_id), None)
        if root is None:
            raise ConfigurationError(f"unknown root id: {root_id}")

        mapping_index = self.effective_mappings(include_candidates=include_candidates)
        matched_mappings = tuple(
            row
            for _, row in sorted(mapping_index.items())
            if root_id == row.get("primary_root") or root_id in row.get("secondary_roots", [])
        )
        card_ids = {str(row["card_id"]) for row in matched_mappings}
        allowed_card_status = {"confirmed", "candidate"} if include_candidates else {"confirmed"}
        cards = tuple(
            row
            for row in self._records("cards")
            if str(row.get("id")) in card_ids and row.get("status") in allowed_card_status
        )

        allowed_status = {"confirmed", "candidate"} if include_candidates else {"confirmed"}
        principles = tuple(
            row
            for row in _effective_versions(
                self._records("principles"), include_candidates=include_candidates
            )
            if row.get("status") in allowed_status
            and (row.get("primary_root") == root_id or root_id in row.get("secondary_roots", []))
        )
        cases = tuple(
            row
            for row in _effective_versions(
                self._records("cases"), include_candidates=include_candidates
            )
            if row.get("status") in allowed_status
            and (row.get("primary_root") == root_id or root_id in row.get("secondary_roots", []))
        )
        return RootContext(
            root=root,
            mappings=matched_mappings,
            cards=cards,
            principles=principles,
            cases=cases,
            includes_candidates=include_candidates,
        )

    def _records(self, key: str) -> list[dict[str, Any]]:
        return read_jsonl(self.root / DATA_FILES[key])


def _effective_versions(
    records: list[dict[str, Any]], *, include_candidates: bool = False
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        record_id = str(row.get("id", ""))
        if not record_id:
            continue
        grouped[record_id].append(row)

    current: dict[str, dict[str, Any]] = {}
    for record_id, rows in grouped.items():
        human = [row for row in rows if row.get("status") in {"confirmed", "rejected"}]
        if human:
            latest = max(human, key=lambda row: int(row.get("version", 0)))
            if latest.get("status") == "confirmed":
                current[record_id] = latest
            continue
        if include_candidates:
            candidates = [row for row in rows if row.get("status") == "candidate"]
            if candidates:
                current[record_id] = max(candidates, key=lambda row: int(row.get("version", 0)))
    return [current[key] for key in sorted(current)]


def _rejected_mapping_keys(verdicts: list[dict[str, Any]]) -> set[tuple[str, int]]:
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for row in verdicts:
        if row.get("object_type") != "mapping":
            continue
        key = (str(row.get("object_id")), int(row.get("object_version", 0)))
        previous = latest.get(key)
        if previous is None or int(row.get("ledger_version", 0)) > int(
            previous.get("ledger_version", 0)
        ):
            latest[key] = row
    return {key for key, row in latest.items() if row.get("verdict") == "rejected"}


def _score(query: str, text: str) -> float:
    query_normalized = _normalize_text(query)
    text_normalized = _normalize_text(text)
    if not query_normalized or not text_normalized:
        return 0.0
    score = 8.0 if query_normalized in text_normalized else 0.0
    query_terms = _terms(query_normalized)
    text_terms = _terms(text_normalized)
    for term in query_terms:
        if term in text_terms:
            score += 2.0
        elif term in text_normalized:
            score += 1.0
    return round(score, 3)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _terms(value: str) -> set[str]:
    terms: set[str] = set()
    for token in re.findall(r"[\w\u4e00-\u9fff]+", value, flags=re.UNICODE):
        terms.add(token)
        if len(token) >= 3 and any("\u4e00" <= char <= "\u9fff" for char in token):
            terms.update(token[index : index + 2] for index in range(len(token) - 1))
    return terms
