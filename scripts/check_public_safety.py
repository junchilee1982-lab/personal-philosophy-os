#!/usr/bin/env python3
"""Fail closed when a public release contains private data or secret-shaped text.

Diagnostics intentionally contain only a rule ID, relative path and line number.
Matched text is never printed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024

FORBIDDEN_TOP_LEVEL = {
    "库",
    "原料",
    "候补",
    "案例",
    "蒸馏",
    "镜子反馈",
    "出口",
    "_tmp",
}
FORBIDDEN_PARTS = {
    "shadow",
    "staging",
    "transactions",
    "_事务",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {".log", ".pyc", ".bak", ".tmp"}
PRIVATE_RUNTIME_FILES = {
    "root-mappings.jsonl",
    "external-sources.jsonl",
    "verdicts.jsonl",
}
REQUIRED_PATHS = {
    "README.md",
    "LICENSE",
    "PRIVACY.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    "skills/personal-thought-vault/SKILL.md",
    "schemas/card.schema.json",
    "tests",
}


def _content_rules() -> list[tuple[str, re.Pattern[str]]]:
    user_path = "/" + "Users" + r"/[^/\s]+/"
    home_path = "/" + "home" + r"/[^/\s]+/"
    win_path = r"[A-Za-z]:\\" + "Users" + r"\\[^\\\s]+\\"
    bearer = "Authorization" + r"\s*:\s*" + "Bearer" + r"\s+[A-Za-z0-9._~+/-]{8,}"
    github_token = "gh" + r"[pousr]_[A-Za-z0-9]{20,}"
    github_fine_grained = "github" + r"_pat_[A-Za-z0-9_]{20,}"
    openai_token = "s" + r"k-(?:proj-)?[A-Za-z0-9_-]{20,}"
    anthropic_token = "s" + r"k-ant-[A-Za-z0-9_-]{20,}"
    slack_token = "x" + r"ox[baprs]-[A-Za-z0-9-]{10,}"
    private_key = "BEGIN" + r" [A-Z ]*PRIVATE KEY"
    api_assignment = r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*['\"]?(?!example|<|\$\{)[A-Za-z0-9._/+~-]{12,}"
    email = (
        r"(?i)\b[A-Z0-9._%+-]+@(?![A-Z0-9.-]*example\.(?:com|org|net)\b)[A-Z0-9.-]+\.[A-Z]{2,}\b"
    )
    phone = r"(?<!\d)1[3-9]\d{9}(?!\d)"
    return [
        ("P004", re.compile(user_path)),
        ("P004", re.compile(home_path)),
        ("P004", re.compile(win_path)),
        ("P005", re.compile(bearer)),
        ("P005", re.compile(github_token)),
        ("P005", re.compile(github_fine_grained)),
        ("P005", re.compile(openai_token)),
        ("P005", re.compile(anthropic_token)),
        ("P005", re.compile(slack_token)),
        ("P005", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("P005", re.compile(r"ASIA[0-9A-Z]{16}")),
        ("P005", re.compile(private_key)),
        ("P005", re.compile(api_assignment)),
        ("P006", re.compile(email)),
        ("P006", re.compile(phone)),
    ]


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int = 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="scan all public worktree files")
    group.add_argument("--tracked", action="store_true", help="scan Git-tracked files")
    group.add_argument("--artifact", type=Path, help="scan an unpacked release artifact")
    parser.add_argument("--history-paths", action="store_true")
    args = parser.parse_args(argv)

    if args.artifact:
        artifact_root = args.artifact.expanduser().resolve(strict=False)
        if not artifact_root.is_dir():
            print("P012 .")
            print("public safety: artifact directory does not exist", file=sys.stderr)
            return 1
        paths = _all_paths(artifact_root)
        return _print_findings(_scan_paths(paths, base=artifact_root), len(paths))

    is_git = _is_git_repo()
    if (args.tracked or args.history_paths) and not is_git:
        print("P011 .")
        print(
            "public safety: Git history was requested but no Git repository exists", file=sys.stderr
        )
        return 1
    paths = _all_paths() if args.all or not is_git else _tracked_paths()
    findings = _check_required(paths)
    findings.extend(_scan_paths(paths, base=ROOT))
    if args.history_paths and _is_git_repo():
        findings.extend(_scan_history_paths())

    return _print_findings(findings, len(paths))


def _print_findings(findings: list[Finding], file_count: int) -> int:
    unique = sorted(set(findings), key=lambda item: (item.rule, item.path, item.line))
    for finding in unique:
        suffix = f":{finding.line}" if finding.line else ""
        print(f"{finding.rule} {finding.path}{suffix}")
    if unique:
        print(f"public safety: failed with {len(unique)} finding(s)", file=sys.stderr)
        return 1
    print(f"public safety: passed ({file_count} files)")
    return 0


def _scan_paths(paths: list[Path], *, base: Path) -> list[Finding]:
    findings: list[Finding] = []
    denylist = _local_denylist()
    rules = _content_rules()
    for path in paths:
        relative = path.relative_to(base).as_posix()
        parts = Path(relative).parts
        if any(part in FORBIDDEN_TOP_LEVEL for part in parts):
            findings.append(Finding("P001", relative))
        if any(part in FORBIDDEN_PARTS for part in parts):
            findings.append(Finding("P003", relative))
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name == ".DS_Store":
            findings.append(Finding("P003", relative))
        normalized_path = "/" + relative
        if (
            path.name in PRIVATE_RUNTIME_FILES
            and "/examples/synthetic-vault/" not in normalized_path
        ):
            findings.append(Finding("P002", relative))
        try:
            payload = path.read_bytes()
        except OSError:
            findings.append(Finding("P009", relative))
            continue
        if len(payload) > MAX_BYTES:
            findings.append(Finding("P009", relative))
            continue
        if b"\x00" in payload:
            findings.append(Finding("P009", relative))
            continue
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            findings.append(Finding("P009", relative))
            continue
        folded_path = relative.casefold()
        if any(value in folded_path for value in denylist):
            findings.append(Finding("P007", relative))
        for line_number, line in enumerate(text.split("\n"), start=1):
            for rule_id, pattern in rules:
                if pattern.search(line):
                    findings.append(Finding(rule_id, relative, line_number))
            folded = line.casefold()
            if any(value in folded for value in denylist):
                findings.append(Finding("P007", relative, line_number))
        if path.suffix == ".jsonl":
            findings.extend(_check_jsonl(relative, text))
    return findings


def _check_jsonl(relative: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    normalized = "/" + relative
    allowed = "/examples/synthetic-vault/" in normalized or "/templates/" in normalized
    if not allowed:
        return [Finding("P008", relative)]
    for line_number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            findings.append(Finding("P008", relative, line_number))
            continue
        if not isinstance(value, dict) or value.get("synthetic") is not True:
            findings.append(Finding("P008", relative, line_number))
    return findings


def _check_required(paths: list[Path]) -> list[Finding]:
    relatives = {path.relative_to(ROOT).as_posix() for path in paths}
    findings: list[Finding] = []
    for required in REQUIRED_PATHS:
        target = ROOT / required
        if target.is_dir():
            if not any(item.startswith(required + "/") for item in relatives):
                findings.append(Finding("P010", required))
        elif required not in relatives:
            findings.append(Finding("P010", required))
    return findings


def _scan_history_paths() -> list[Finding]:
    result = subprocess.run(
        ["git", "log", "--all", "--name-only", "--format="],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    findings: list[Finding] = []
    for raw in result.stdout.split("\n"):
        relative = raw.strip()
        if not relative:
            continue
        parts = Path(relative).parts
        if any(part in FORBIDDEN_TOP_LEVEL for part in parts):
            findings.append(Finding("H001", relative))
        if any(part in FORBIDDEN_PARTS for part in parts):
            findings.append(Finding("H003", relative))
        if Path(relative).suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(Finding("H003", relative))
        if Path(relative).name in PRIVATE_RUNTIME_FILES and "/examples/synthetic-vault/" not in (
            "/" + relative
        ):
            findings.append(Finding("H002", relative))
    return findings


def _local_denylist() -> tuple[str, ...]:
    path = ROOT / ".privacy-denylist.local"
    if not path.is_file():
        return ()
    values: list[str] = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        value = line.strip().casefold()
        if value and not value.startswith("#"):
            values.append(value)
    return tuple(values)


def _all_paths(base: Path = ROOT) -> list[Path]:
    excluded = {
        ".git",
        ".venv",
        "build",
        "dist",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        ".nox",
    }
    result: list[Path] = []
    for path in base.rglob("*"):
        relative = path.relative_to(base)
        if any(part in excluded or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.name == ".privacy-denylist.local" or not path.is_file():
            continue
        result.append(path)
    return sorted(result)


def _tracked_paths() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
    paths: list[Path] = []
    for value in result.stdout.split(b"\x00"):
        if not value:
            continue
        relative = value.decode("utf-8", errors="strict")
        path = ROOT / relative
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def _is_git_repo() -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "true"


if __name__ == "__main__":
    raise SystemExit(main())
