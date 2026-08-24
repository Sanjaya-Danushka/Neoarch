"""Structured error classification for package operations.

Classifies raw error output from pacman, AUR helpers, Flatpak, npm, and
other backends into structured results that the UI can display with
appropriate titles, messages, and action buttons.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


__all__ = ["OperationResult", "classify_error", "classify_aur_output"]


@dataclass
class OperationResult:
    """Structured result of a package operation failure.

    Attributes:
        category: Machine-readable category (network_error, aur_unavailable, etc.)
        title: Short user-facing title (e.g. "Network error")
        message: One-sentence explanation of what happened
        details: Raw error text for "View Details"
        retryable: Whether the operation can be retried
        action: Primary action hint ("retry", "authenticate", "view_log", "none")
        packages: List of specific packages that failed (if applicable)
    """
    category: str = "unknown"
    title: str = "Operation failed"
    message: str = "An unexpected error occurred."
    details: str = ""
    retryable: bool = False
    action: str = "none"
    packages: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern tables — each entry is (compiled_regex, category, title, message, retryable, action)
# Order matters: first match wins.
# ---------------------------------------------------------------------------

_NETWORK_PATTERNS = [
    (re.compile(r'could not resolve host', re.I),
     "network_error", "Network error",
     "NeoArch couldn't reach the package source. Check your internet connection.",
     True, "retry"),
    (re.compile(r'connection refused', re.I),
     "network_error", "Network error",
     "The connection was refused. The server may be temporarily unavailable.",
     True, "retry"),
    (re.compile(r'connection timed out', re.I),
     "network_error", "Network error",
     "The connection timed out. Check your network and try again.",
     True, "retry"),
    (re.compile(r'network is unreachable', re.I),
     "network_error", "Network error",
     "The network is unreachable. Check your network connection.",
     True, "retry"),
    (re.compile(r'no route to host', re.I),
     "network_error", "Network error",
     "No route to the host. Check your network connection.",
     True, "retry"),
    (re.compile(r'name or service not known', re.I),
     "network_error", "Network error",
     "DNS resolution failed. Check your DNS settings.",
     True, "retry"),
    (re.compile(r'failed to connect', re.I),
     "network_error", "Network error",
     "Failed to connect to the remote host.",
     True, "retry"),
    (re.compile(r'winerror|errno\s*=\s*11001', re.I),
     "network_error", "Network error",
     "DNS resolution failed.",
     True, "retry"),
]

_AUR_PATTERNS = [
    (re.compile(r'error downloading.*aur', re.I),
     "aur_unavailable", "AUR unavailable",
     "The Arch User Repository could not be reached.",
     True, "retry"),
    (re.compile(r'failed to clone.*aur', re.I),
     "aur_unavailable", "AUR unavailable",
     "Could not clone from the AUR. The repository may be temporarily down.",
     True, "retry"),
    (re.compile(r'unable to fetch', re.I),
     "aur_unavailable", "AUR unavailable",
     "Could not fetch package data from the AUR.",
     True, "retry"),
    (re.compile(r'aur.*(?:timeout|timed out)', re.I),
     "aur_unavailable", "AUR unavailable",
     "The AUR request timed out.",
     True, "retry"),
]

_TIMEOUT_PATTERNS = [
    (re.compile(r'tim?ed?\s*out', re.I),
     "timeout", "Operation timed out",
     "The operation took too long and was stopped.",
     True, "retry"),
]

_AUTH_PATTERNS = [
    (re.compile(r'no askpass program specified', re.I),
     "authentication_required", "Authentication required",
     "Authentication failed. Start the operation again and enter your password in the NeoArch dialog.",
     False, "authenticate"),
    (re.compile(r'authentication (?:failed|agent)', re.I),
     "authentication_required", "Authentication required",
     "The password dialog was dismissed or failed.",
     True, "authenticate"),
    (re.compile(r'sudo:\s*(?:no tty|not a tty)', re.I),
     "authentication_required", "Authentication required",
     "Cannot prompt for password in this context.",
     False, "authenticate"),
    (re.compile(r'permission denied', re.I),
     "permission_denied", "Permission denied",
     "Insufficient permissions. Administrator access may be required.",
     True, "authenticate"),
    (re.compile(r'EACCES', re.I),
     "permission_denied", "Permission denied",
     "Insufficient permissions for this operation.",
     True, "authenticate"),
]

_BUILD_PATTERNS = [
    (re.compile(r'could not satisfy dependencies', re.I),
     "build_failed", "Dependency conflict",
     "A dependency conflict prevented the operation from completing.",
     False, "view_log"),
    (re.compile(r'a failure occurred in build', re.I),
     "build_failed", "Package build failed",
     "The package could not be built. Check the build log for details.",
     False, "view_log"),
    (re.compile(r'error making:\s*(.+?):', re.I),
     "build_failed", "Package build failed",
     "The package could not be built.",
     False, "view_log"),
    (re.compile(r'exit status \d+', re.I),
     "build_failed", "Package build failed",
     "The build process exited with an error.",
     False, "view_log"),
    (re.compile(r'failed to build', re.I),
     "build_failed", "Package build failed",
     "The package failed to build.",
     False, "view_log"),
    (re.compile(r'makepkg.*failed', re.I),
     "build_failed", "Package build failed",
     "makepkg failed to build the package.",
     False, "view_log"),
]

_PACKAGE_PATTERNS = [
    (re.compile(r'not found in remote repositories', re.I),
     "package_not_found", "Package not found",
     "The package was not found in any configured repository.",
     False, "none"),
    (re.compile(r'could not find', re.I),
     "package_not_found", "Package not found",
     "The package could not be found.",
     False, "none"),
    (re.compile(r'no results', re.I),
     "package_not_found", "Package not found",
     "No results were found for this package.",
     False, "none"),
    (re.compile(r'package .* does not exist', re.I),
     "package_not_found", "Package not found",
     "The specified package does not exist.",
     False, "none"),
]

_HELPER_PATTERNS = [
    (re.compile(r'no aur helper available', re.I),
     "helper_missing", "AUR helper missing",
     "No AUR helper found. Install yay, paru, trizen, or pikaur.",
     False, "none"),
    (re.compile(r'(?:yay|paru|trizen|pikaur).*not found', re.I),
     "helper_missing", "AUR helper missing",
     "The configured AUR helper is not installed.",
     False, "none"),
]

_CANCELLED_PATTERNS = [
    (re.compile(r'cancelled by user', re.I),
     "cancelled", "Operation cancelled",
     "The operation was cancelled by the user.",
     False, "none"),
    (re.compile(r'intercepted.*sigint', re.I),
     "cancelled", "Operation cancelled",
     "The operation was interrupted.",
     False, "none"),
]

_OWNERSHIP_PATTERNS = [
    (re.compile(r'cannot change ownership.*value too large', re.I),
     "build_failed", "Package build failed",
     "tar failed to set file ownership. Add '--no-same-owner' to the tar command in the PKGBUILD.",
     False, "view_log"),
]


def classify_error(text: str, source: str = "") -> OperationResult:
    """Classify raw error text into a structured OperationResult.

    Args:
        text: Combined stderr/error output from the failed operation.
        source: Package source (AUR, pacman, Flatpak, npm) for context.

    Returns:
        OperationResult with category, title, message, and action hints.
    """
    if not text:
        return OperationResult(
            category="unknown",
            title="Operation failed",
            message="The operation failed with no error output.",
        )

    # Check patterns in priority order
    all_patterns = (
        _CANCELLED_PATTERNS
        + _AUTH_PATTERNS
        + _NETWORK_PATTERNS
        + _AUR_PATTERNS
        + _TIMEOUT_PATTERNS
        + _OWNERSHIP_PATTERNS
        + _BUILD_PATTERNS
        + _PACKAGE_PATTERNS
        + _HELPER_PATTERNS
    )

    for pattern, category, title, message, retryable, action in all_patterns:
        if pattern.search(text):
            return OperationResult(
                category=category,
                title=title,
                message=message,
                details=text,
                retryable=retryable,
                action=action,
            )

    # AUR-specific: check for build failures that mention specific packages
    if source == "AUR":
        failed_pkgs = _extract_failed_packages(text)
        if failed_pkgs:
            return OperationResult(
                category="build_failed",
                title="Package build failed",
                message=f"Failed to build: {', '.join(failed_pkgs)}.",
                details=text,
                retryable=False,
                action="view_log",
                packages=failed_pkgs,
            )

    return OperationResult(
        category="unknown",
        title="Operation failed",
        message="An unexpected error occurred. Check the console for details.",
        details=text,
    )


def classify_aur_output(text: str) -> OperationResult:
    """Classify AUR helper (yay/paru) output specifically.

    Convenience wrapper that always applies AUR context.
    """
    return classify_error(text, source="AUR")


def _extract_failed_packages(text: str) -> List[str]:
    """Extract package names from AUR error output."""
    packages = []
    # yay format: "error making: <pkg>: <reason>"
    for m in re.finditer(r'error making:\s*([^:]+?):', text or ''):
        name = m.group(1).strip()
        if name and name not in packages:
            packages.append(name)
    # paru format: "Failed to install ... <pkg> - <reason>"
    for m in re.finditer(r'failed to install.*?(\S+)\s*-', text or '', re.I):
        name = m.group(1).strip()
        if name and name not in packages:
            packages.append(name)
    return packages
