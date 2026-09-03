"""Permission definitions and risk classification."""
from enum import Enum


class RiskLevel(str, Enum):
    """Risk classification for tool actions."""
    SAFE = "SAFE"            # Read operations, listing, searching
    MODERATE = "MODERATE"    # Creating new files, creating folders
    RISKY = "RISKY"          # Overwriting, deleting, launching external apps, system changes
    BLOCKED = "BLOCKED"      # Arbitrary commands, unauthorized access


class SecurityException(Exception):
    """Base exception for security violations."""
    pass


class AccessDeniedError(SecurityException):
    """Raised when an action or path violates security policy."""
    pass


class ActionCancelledError(SecurityException):
    """Raised when user denies confirmation for a risky action."""
    pass
