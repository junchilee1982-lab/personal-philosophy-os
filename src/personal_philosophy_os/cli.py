"""Command-line interface for Personal Philosophy OS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .config import remember_vault, resolve_vault_path
from .errors import PPOSError, VaultValidationError
from .skill_manager import install_skill, skill_status, uninstall_skill
from .validation import validate_vault
from .vault import init_vault, open_vault


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppos", description="Local-first Personal Philosophy OS")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize a Vault")
    init_parser.add_argument("--vault", required=True)
    init_parser.add_argument("--demo", action="store_true", help="add synthetic demo records")
    init_parser.set_defaults(handler=_cmd_init)

    data_parser = subparsers.add_parser("data", help="manage the default Vault")
    data_sub = data_parser.add_subparsers(dest="data_command", required=True)
    data_use = data_sub.add_parser("use", help="validate and remember a Vault path")
    data_use.add_argument("path")
    data_use.set_defaults(handler=_cmd_data_use)

    validate_parser = subparsers.add_parser("validate", help="validate a Vault")
    _add_vault_json_args(validate_parser)
    validate_parser.set_defaults(handler=_cmd_validate)

    doctor_parser = subparsers.add_parser("doctor", help="inspect local installation health")
    _add_vault_json_args(doctor_parser)
    doctor_parser.set_defaults(handler=_cmd_doctor)

    search_parser = subparsers.add_parser("search", help="search evidence or conclusions")
    search_parser.add_argument("query")
    search_parser.add_argument("--vault")
    search_parser.add_argument("--channel", choices=("evidence", "conclusion"), default="evidence")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--json", action="store_true")
    search_parser.set_defaults(handler=_cmd_search)

    context_parser = subparsers.add_parser("context", help="assemble root-question context")
    context_parser.add_argument("root_id")
    context_parser.add_argument("--vault")
    context_parser.add_argument("--include-candidates", action="store_true")
    context_parser.add_argument("--json", action="store_true")
    context_parser.set_defaults(handler=_cmd_context)

    mode_parser = subparsers.add_parser("mode", help="show or set rollout mode")
    mode_sub = mode_parser.add_subparsers(dest="mode_command", required=True)
    mode_show = mode_sub.add_parser("show")
    mode_show.add_argument("--vault")
    mode_show.add_argument("--json", action="store_true")
    mode_show.set_defaults(handler=_cmd_mode_show)
    mode_set = mode_sub.add_parser("set")
    mode_set.add_argument("mode", choices=("stable", "shadow", "active"))
    mode_set.add_argument("--vault")
    mode_set.add_argument("--confirm", action="store_true")
    mode_set.set_defaults(handler=_cmd_mode_set)

    skill_parser = subparsers.add_parser("skill", help="install or remove the agent skill")
    skill_sub = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_install = skill_sub.add_parser("install")
    _add_skill_args(skill_install)
    skill_install.add_argument("--force", action="store_true")
    skill_install.set_defaults(handler=_cmd_skill_install)
    skill_uninstall = skill_sub.add_parser("uninstall")
    _add_skill_args(skill_uninstall)
    skill_uninstall.set_defaults(handler=_cmd_skill_uninstall)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except PPOSError as exc:
        print(f"ppos: {exc}", file=sys.stderr)
        return exc.exit_code
    except PermissionError:
        print("ppos: permission denied", file=sys.stderr)
        return 5
    except OSError as exc:
        print(f"ppos: operating-system error: {exc.__class__.__name__}", file=sys.stderr)
        return 4


def _cmd_init(args: argparse.Namespace) -> int:
    vault = init_vault(args.vault, demo=args.demo)
    print(f"Initialized Vault: {vault.root}")
    return 0


def _cmd_data_use(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve(strict=False)
    report = validate_vault(path)
    if not report.valid:
        raise VaultValidationError("cannot remember an invalid Vault")
    config_path = remember_vault(path)
    print(f"Default Vault: {path}")
    print(f"User config: {config_path}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = resolve_vault_path(args.vault)
    try:
        report = validate_vault(path)
    except Exception:
        result = _invalid_validation_result()
    else:
        result = _validation_result(report.to_dict(), path)
    if args.json:
        _print_json(result)
    else:
        label = "valid" if result["valid"] else "invalid"
        print(
            f"Vault {label}: {result['checked_files']} files, {result['checked_records']} records"
        )
        for issue in result["issues"]:
            location = f"{issue['path']}:{issue['line']}" if issue["line"] else issue["path"]
            print(f"- {issue['code']} {location}: {issue['message']}")
    return 0 if result["valid"] else 3


def _cmd_doctor(args: argparse.Namespace) -> int:
    path = resolve_vault_path(args.vault)
    try:
        report = validate_vault(path)
    except Exception:
        validation = _invalid_validation_result()
    else:
        validation = _validation_result(report.to_dict(), path)
    result = {
        "engine_version": __version__,
        "vault_configured": path.exists(),
        "vault_valid": validation["valid"],
        "vault_schema_version": 1 if validation["valid"] else None,
        "skills": skill_status(),
        "network_used": False,
        "telemetry": False,
        "issues": validation["issues"],
    }
    if args.json:
        _print_json(result)
    else:
        print(f"Engine: {__version__}")
        print(f"Vault: {'valid' if report.valid else 'invalid or missing'}")
        print(f"Codex skill: {'installed' if result['skills']['codex'] else 'not installed'}")
        print(f"Claude skill: {'installed' if result['skills']['claude'] else 'not installed'}")
        print("Network: disabled by engine")
        print("Telemetry: none")
    return 0 if validation["valid"] else 3


def _cmd_search(args: argparse.Namespace) -> int:
    vault = open_vault(args.vault)
    hits = vault.search(args.query, channel=args.channel, top_k=args.top_k)
    if args.json:
        _print_json({"channel": args.channel, "hits": [hit.to_dict() for hit in hits]})
    else:
        if not hits:
            print("No confirmed matches.")
        for hit in hits:
            roots = ",".join(hit.root_ids) if hit.root_ids else "unmapped"
            print(f"{hit.record_id} [{roots}] score={hit.score:g}")
            print(hit.text)
    return 0


def _cmd_context(args: argparse.Namespace) -> int:
    vault = open_vault(args.vault)
    context = vault.root_context(args.root_id, include_candidates=args.include_candidates)
    if args.json:
        _print_json(context.to_dict())
    else:
        root = context.root
        print(f"{root['id']}: {root.get('question_zh') or root.get('question_en')}")
        print(
            f"{len(context.principles)} principles, {len(context.cards)} cards, "
            f"{len(context.cases)} cases"
        )
        for principle in context.principles:
            print(f"- {principle['id']}: {principle['statement']}")
    return 0


def _cmd_mode_show(args: argparse.Namespace) -> int:
    vault = open_vault(args.vault)
    if args.json:
        _print_json({"rollout_mode": vault.mode})
    else:
        print(vault.mode)
    return 0


def _cmd_mode_set(args: argparse.Namespace) -> int:
    vault = open_vault(args.vault)
    vault.set_mode(args.mode, confirm=args.confirm)
    print(f"Rollout mode: {args.mode}")
    return 0


def _cmd_skill_install(args: argparse.Namespace) -> int:
    paths = install_skill(
        target=args.target, scope=args.scope, force=args.force, project=Path.cwd()
    )
    for path in paths:
        print(f"Installed: {path}")
    return 0


def _cmd_skill_uninstall(args: argparse.Namespace) -> int:
    paths = uninstall_skill(target=args.target, scope=args.scope, project=Path.cwd())
    for path in paths:
        print(f"Removed: {path}")
    if not paths:
        print("No managed skill installation found.")
    return 0


def _add_vault_json_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vault")
    parser.add_argument("--json", action="store_true")


def _add_skill_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", choices=("codex", "claude", "both"), required=True)
    parser.add_argument("--scope", choices=("user", "project"), default="user")


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _validation_result(result: dict[str, Any], vault: Path) -> dict[str, Any]:
    """Return a validation result safe to expose outside the process."""

    result["vault"] = "<configured-vault>"
    vault_text = str(vault)
    for issue in result["issues"]:
        issue["message"] = issue["message"].replace(vault_text, "<configured-vault>")
    return result


def _invalid_validation_result() -> dict[str, Any]:
    return {
        "valid": False,
        "vault": "<configured-vault>",
        "checked_files": 0,
        "checked_records": 0,
        "issues": [
            {
                "code": "V004",
                "path": ".",
                "message": "Vault data could not be validated",
                "line": None,
                "severity": "error",
            }
        ],
    }
