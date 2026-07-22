"""Small serializable result models used by the public API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    line: int | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    vault: str
    checked_files: int = 0
    checked_records: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def add(
        self,
        code: str,
        path: str,
        message: str,
        *,
        line: int | None = None,
        severity: str = "error",
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                path=path,
                message=message,
                line=line,
                severity=severity,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "vault": self.vault,
            "checked_files": self.checked_files,
            "checked_records": self.checked_records,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class SearchHit:
    kind: str
    record_id: str
    text: str
    score: float
    status: str
    subject_id: str | None = None
    root_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["root_ids"] = list(self.root_ids)
        result["evidence_ids"] = list(self.evidence_ids)
        return result


@dataclass(frozen=True)
class RootContext:
    root: dict[str, Any]
    mappings: tuple[dict[str, Any], ...]
    cards: tuple[dict[str, Any], ...]
    principles: tuple[dict[str, Any], ...]
    cases: tuple[dict[str, Any], ...]
    includes_candidates: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "mappings": list(self.mappings),
            "cards": list(self.cards),
            "principles": list(self.principles),
            "cases": list(self.cases),
            "includes_candidates": self.includes_candidates,
        }
