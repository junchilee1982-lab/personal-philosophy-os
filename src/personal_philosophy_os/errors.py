"""Typed, user-safe errors for the CLI and public API."""


class PPOSError(Exception):
    """Base error with a stable process exit code."""

    exit_code = 4


class ConfigurationError(PPOSError):
    exit_code = 2


class VaultValidationError(PPOSError):
    exit_code = 3


class InstallError(PPOSError):
    exit_code = 4


class AuthorizationError(PPOSError):
    exit_code = 5
