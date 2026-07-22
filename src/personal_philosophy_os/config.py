"""Platform-aware configuration and Vault path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping

from .errors import ConfigurationError
from .io_utils import read_json, write_json

ENV_KEYS = ("PPOS_VAULT", "PERSONAL_THOUGHT_VAULT_HOME")


def platform_config_file(*, home: Path | None = None) -> Path:
    supplied_home = home is not None
    home = home or Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "personal-philosophy-os" / "config.json"
    if os.name == "nt":
        base = (
            home / "AppData" / "Roaming"
            if supplied_home
            else Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        )
        return base / "personal-philosophy-os" / "config.json"
    base = (
        home / ".config"
        if supplied_home
        else Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
    )
    return base / "personal-philosophy-os" / "config.json"


def platform_default_vault(*, home: Path | None = None) -> Path:
    supplied_home = home is not None
    home = home or Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "personal-philosophy-os" / "vault"
    if os.name == "nt":
        base = (
            home / "AppData" / "Local"
            if supplied_home
            else Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        )
        return base / "personal-philosophy-os" / "vault"
    base = (
        home / ".local" / "share"
        if supplied_home
        else Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share")))
    )
    return base / "personal-philosophy-os" / "vault"


def resolve_vault_path(
    cli_path: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    config_file: Path | None = None,
    home: Path | None = None,
) -> Path:
    if cli_path:
        return _normalize(cli_path)

    env = env if env is not None else os.environ
    for key in ENV_KEYS:
        value = env.get(key, "").strip()
        if value:
            return _normalize(value)

    config_path = config_file or platform_config_file(home=home)
    if config_path.exists():
        value = read_json(config_path)
        if not isinstance(value, dict):
            raise ConfigurationError(f"user configuration must be an object: {config_path}")
        configured = value.get("default_vault")
        if configured:
            if not isinstance(configured, str):
                raise ConfigurationError("default_vault must be a string")
            return _normalize(configured)

    return platform_default_vault(home=home).resolve(strict=False)


def remember_vault(path: Path, *, config_file: Path | None = None) -> Path:
    target = config_file or platform_config_file()
    value = {"schema_version": 1, "default_vault": str(path.resolve(strict=False))}
    write_json(target, value)
    return target


def _normalize(value: str | Path) -> Path:
    try:
        return Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ConfigurationError("invalid Vault path") from exc
