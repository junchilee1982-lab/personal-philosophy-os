"""Strict UTF-8 JSON/JSONL helpers with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .errors import VaultValidationError


def read_text_strict(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="strict")
    except FileNotFoundError as exc:
        raise VaultValidationError(f"required file is missing: {path}") from exc
    except UnicodeDecodeError as exc:
        raise VaultValidationError(f"file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise VaultValidationError(f"cannot read file: {path}") from exc


def read_json(path: Path) -> Any:
    try:
        return json.loads(read_text_strict(path))
    except json.JSONDecodeError as exc:
        raise VaultValidationError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}"
        ) from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL using only the newline byte as a record separator."""

    text = read_text_strict(path)
    records: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.split("\n"), start=1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise VaultValidationError(
                f"invalid JSONL in {path} at line {line_number}, column {exc.colno}"
            ) from exc
        if not isinstance(value, dict):
            raise VaultValidationError(
                f"JSONL record must be an object in {path} at line {line_number}"
            )
        records.append(value)
    return records


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    atomic_write_text(path, text)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records]
    atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""))
