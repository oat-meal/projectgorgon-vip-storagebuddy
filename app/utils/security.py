"""
Security utilities for path validation, input sanitization, and safe file operations
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List, Union

from .constants import (
    MAX_FILE_SIZE_MB,
    MAX_JSON_DEPTH,
    MAX_PATH_LENGTH,
    SENSITIVE_LOG_FIELDS,
)

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a security validation fails"""
    pass


class PathTraversalError(SecurityError):
    """Raised when path traversal is detected"""
    pass


class FileSizeError(SecurityError):
    """Raised when file exceeds size limit"""
    pass


def is_safe_path(basedir: Path, path: Path) -> bool:
    """
    Validate that a path is within the allowed base directory.
    Prevents path traversal attacks.

    Args:
        basedir: The allowed base directory
        path: The path to validate

    Returns:
        True if path is safely within basedir
    """
    try:
        # Resolve both paths to absolute, resolving any symlinks
        resolved_base = basedir.resolve()
        resolved_path = path.resolve()

        # Check if the resolved path starts with the base directory
        return resolved_path.is_relative_to(resolved_base)
    except (ValueError, OSError) as e:
        logger.warning(f"Path validation failed: {e}")
        return False


def validate_path(
    path: Union[str, Path],
    basedir: Optional[Path] = None,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    max_size_mb: Optional[float] = None
) -> Path:
    """
    Validate and sanitize a file path.

    Args:
        path: The path to validate
        basedir: If provided, path must be within this directory
        must_exist: If True, path must exist
        must_be_file: If True, path must be a file
        must_be_dir: If True, path must be a directory
        max_size_mb: If provided, file must be smaller than this (in MB)

    Returns:
        Validated Path object

    Raises:
        SecurityError: If validation fails
    """
    # Convert to Path and check length
    if isinstance(path, str):
        if len(path) > MAX_PATH_LENGTH:
            raise SecurityError(f"Path too long (max {MAX_PATH_LENGTH} chars)")
        path = Path(path)

    # Resolve to absolute path
    try:
        resolved = path.resolve()
    except (OSError, ValueError) as e:
        raise SecurityError(f"Invalid path: {e}")

    # Check for null bytes (common injection technique)
    if '\x00' in str(resolved):
        raise SecurityError("Path contains null bytes")

    # Validate against base directory if provided
    if basedir is not None:
        if not is_safe_path(basedir, resolved):
            raise PathTraversalError(
                f"Path '{path}' is outside allowed directory '{basedir}'"
            )

    # Check existence
    if must_exist and not resolved.exists():
        raise SecurityError(f"Path does not exist: {path}")

    # Check type
    if must_be_file and resolved.exists() and not resolved.is_file():
        raise SecurityError(f"Path is not a file: {path}")

    if must_be_dir and resolved.exists() and not resolved.is_dir():
        raise SecurityError(f"Path is not a directory: {path}")

    # Check file size
    if max_size_mb is not None and resolved.is_file():
        size_mb = resolved.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise FileSizeError(
                f"File too large: {size_mb:.1f}MB (max {max_size_mb}MB)"
            )

    return resolved


def safe_read_json(
    path: Path,
    basedir: Optional[Path] = None,
    max_size_mb: float = MAX_FILE_SIZE_MB,
    encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """
    Safely read and parse a JSON file with security checks.

    Args:
        path: Path to JSON file
        basedir: If provided, file must be within this directory
        max_size_mb: Maximum file size in MB
        encoding: File encoding

    Returns:
        Parsed JSON data

    Raises:
        SecurityError: If security validation fails
        json.JSONDecodeError: If JSON parsing fails
    """
    # Validate path
    validated_path = validate_path(
        path,
        basedir=basedir,
        must_exist=True,
        must_be_file=True,
        max_size_mb=max_size_mb
    )

    # Read and parse
    with open(validated_path, 'r', encoding=encoding) as f:
        return json.load(f)


def sanitize_log_data(data: Any, depth: int = 0) -> Any:
    """
    Sanitize data for logging by redacting sensitive fields.

    Args:
        data: Data to sanitize (dict, list, or primitive)
        depth: Current recursion depth

    Returns:
        Sanitized copy of data
    """
    if depth > MAX_JSON_DEPTH:
        return "[DEPTH_LIMIT]"

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if key contains sensitive terms
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in SENSITIVE_LOG_FIELDS):
                result[key] = "[REDACTED]"
            else:
                result[key] = sanitize_log_data(value, depth + 1)
        return result

    elif isinstance(data, list):
        return [sanitize_log_data(item, depth + 1) for item in data[:100]]  # Limit list size

    elif isinstance(data, str):
        # Truncate long strings
        if len(data) > 500:
            return data[:500] + "...[TRUNCATED]"
        return data

    else:
        return data


def validate_json_depth(data: Any, max_depth: int = MAX_JSON_DEPTH, current_depth: int = 0) -> bool:
    """
    Validate that JSON data doesn't exceed maximum nesting depth.

    Args:
        data: JSON data to validate
        max_depth: Maximum allowed depth
        current_depth: Current recursion depth

    Returns:
        True if within limits

    Raises:
        SecurityError: If depth exceeds limit
    """
    if current_depth > max_depth:
        raise SecurityError(f"JSON nesting too deep (max {max_depth} levels)")

    if isinstance(data, dict):
        for value in data.values():
            validate_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            validate_json_depth(item, max_depth, current_depth + 1)

    return True


def set_secure_file_permissions(path: Path, mode: int = 0o600) -> None:
    """
    Set secure permissions on a file (owner read/write only).

    Args:
        path: Path to file
        mode: Permission mode (default: 600 = owner read/write only)
    """
    try:
        os.chmod(path, mode)
    except OSError as e:
        logger.warning(f"Failed to set permissions on {path}: {e}")


def set_secure_dir_permissions(path: Path, mode: int = 0o700) -> None:
    """
    Set secure permissions on a directory (owner read/write/execute only).

    Args:
        path: Path to directory
        mode: Permission mode (default: 700 = owner only)
    """
    try:
        os.chmod(path, mode)
    except OSError as e:
        logger.warning(f"Failed to set permissions on {path}: {e}")
