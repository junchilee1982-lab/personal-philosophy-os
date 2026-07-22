"""Safe installation and removal of the bundled agent skill."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from importlib.resources import files
from pathlib import Path
from typing import Iterable

from . import __version__
from .errors import ConfigurationError, InstallError

SKILL_NAME = "personal-thought-vault"
MARKER = ".ppos-managed.json"
PRODUCT_NAME = "personal-philosophy-os"


def install_skill(
    *,
    target: str,
    scope: str = "user",
    force: bool = False,
    home: Path | None = None,
    project: Path | None = None,
) -> list[Path]:
    destinations = _destinations(target, scope, home=home, project=project)
    target_names = ("codex", "claude") if target == "both" else (target,)
    source = Path(str(files("personal_philosophy_os").joinpath("skill_bundle", SKILL_NAME)))
    if not (source / "SKILL.md").is_file():
        raise InstallError("bundled skill is missing from this installation")

    for target_name, destination in zip(target_names, destinations):
        if (
            _path_exists(destination)
            and not _is_managed_installation(destination, target=target_name, scope=scope)
            and not force
        ):
            raise InstallError(
                f"refusing to overwrite an unmanaged skill: {destination}; use --force explicitly"
            )

    installation_id = str(uuid.uuid4())
    states: list[dict[str, object]] = []
    for target_name, destination in zip(target_names, destinations):
        destination.parent.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        temporary = destination.parent / f".{SKILL_NAME}.install-{token}"
        backup = destination.parent / f".{SKILL_NAME}.backup-{token}"
        try:
            shutil.copytree(source, temporary)
            marker = {
                "product": PRODUCT_NAME,
                "version": __version__,
                "skill": SKILL_NAME,
                "installation_id": installation_id,
                "target": target_name,
                "scope": scope,
            }
            (temporary / MARKER).write_text(
                json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except Exception as exc:
            for state in states:
                _remove_path(state["temporary"])
            _remove_path(temporary)
            raise InstallError(f"skill preparation failed: {destination}") from exc
        states.append(
            {
                "destination": destination,
                "temporary": temporary,
                "backup": backup,
                "had_existing": _path_exists(destination),
                "backed_up": False,
                "committed": False,
            }
        )

    try:
        for state in states:
            destination = state["destination"]
            temporary = state["temporary"]
            backup = state["backup"]
            if state["had_existing"]:
                os.replace(destination, backup)
                state["backed_up"] = True
            os.replace(temporary, destination)
            state["committed"] = True
    except Exception as exc:
        for state in reversed(states):
            destination = state["destination"]
            temporary = state["temporary"]
            backup = state["backup"]
            if state["committed"]:
                _remove_path(destination)
            if state["backed_up"] and _path_exists(backup):
                os.replace(backup, destination)
            _remove_path(temporary)
        raise InstallError("skill installation transaction rolled back") from exc

    for state in states:
        _remove_path(state["backup"])
    return destinations


def uninstall_skill(
    *,
    target: str,
    scope: str = "user",
    home: Path | None = None,
    project: Path | None = None,
) -> list[Path]:
    destinations = _destinations(target, scope, home=home, project=project)
    target_names = ("codex", "claude") if target == "both" else (target,)

    removed: list[Path] = []
    for target_name, destination in zip(target_names, destinations):
        if not _path_exists(destination):
            continue
        if not _is_managed_installation(destination, target=target_name, scope=scope):
            raise InstallError(f"refusing to remove an unmanaged skill: {destination}")
        removed.append(destination)

    if not removed:
        return []

    backups = [
        destination.parent / f".{SKILL_NAME}.uninstall-{uuid.uuid4().hex}"
        for destination in removed
    ]
    renamed: list[tuple[Path, Path]] = []
    try:
        for destination, backup in zip(removed, backups):
            os.replace(destination, backup)
            renamed.append((destination, backup))
    except Exception as exc:
        rollback_errors: list[Exception] = []
        for destination, backup in reversed(renamed):
            try:
                os.replace(backup, destination)
            except Exception as rollback_exc:  # pragma: no cover - catastrophic filesystem failure
                rollback_errors.append(rollback_exc)
        if rollback_errors:
            raise InstallError(
                "skill uninstall transaction could not be fully rolled back"
            ) from exc
        raise InstallError("skill uninstall transaction rolled back") from exc

    for backup in backups:
        _remove_path(backup)
    return removed


def skill_status(*, home: Path | None = None) -> dict[str, bool]:
    home = home or Path.home()
    return {
        "codex": (
            (home / ".agents" / "skills" / SKILL_NAME / "SKILL.md").is_file()
            or (home / ".codex" / "skills" / SKILL_NAME / "SKILL.md").is_file()
        ),
        "claude": (home / ".claude" / "skills" / SKILL_NAME / "SKILL.md").is_file(),
    }


def _destinations(
    target: str,
    scope: str,
    *,
    home: Path | None,
    project: Path | None,
) -> list[Path]:
    if target not in {"codex", "claude", "both"}:
        raise ConfigurationError("target must be codex, claude, or both")
    if scope not in {"user", "project"}:
        raise ConfigurationError("scope must be user or project")
    selected: Iterable[str] = ("codex", "claude") if target == "both" else (target,)
    if scope == "user":
        base = home or Path.home()
    else:
        base = (project or Path.cwd()).resolve(strict=False)
    roots = {"codex": ".agents", "claude": ".claude"}
    return [base / roots[name] / "skills" / SKILL_NAME for name in selected]


def _path_exists(path: object) -> bool:
    return os.path.lexists(Path(path))


def _is_managed_installation(destination: Path, *, target: str, scope: str) -> bool:
    try:
        marker_text = (destination / MARKER).read_bytes().decode("utf-8", errors="strict")
        marker = json.loads(
            marker_text,
            object_pairs_hook=_json_object_without_duplicates,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, ValueError, RecursionError):
        return False

    if not isinstance(marker, dict):
        return False
    installation_id = marker.get("installation_id")
    if not isinstance(installation_id, str):
        return False
    try:
        parsed_installation_id = uuid.UUID(installation_id)
    except (AttributeError, ValueError):
        return False

    return (
        parsed_installation_id.version == 4
        and str(parsed_installation_id) == installation_id
        and marker.get("product") == PRODUCT_NAME
        and marker.get("skill") == SKILL_NAME
        and marker.get("target") == target
        and marker.get("scope") == scope
    )


def _json_object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant: {value}")


def _remove_path(path: object) -> None:
    target = Path(path)
    if not _path_exists(target):
        return
    if target.is_symlink() or target.is_file():
        target.unlink()
    else:
        shutil.rmtree(target)
