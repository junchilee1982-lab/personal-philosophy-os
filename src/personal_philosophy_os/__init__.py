"""Public API for Personal Philosophy OS."""

from .models import RootContext, SearchHit, ValidationIssue, ValidationReport
from .validation import validate_vault
from .vault import Vault, init_vault, open_vault

__all__ = [
    "RootContext",
    "SearchHit",
    "ValidationIssue",
    "ValidationReport",
    "Vault",
    "init_vault",
    "open_vault",
    "validate_vault",
]

__version__ = "0.1.0a1"
