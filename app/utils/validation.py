"""
Input validation utilities
"""

import re
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field

from .constants import (
    MAX_QUERY_LENGTH,
    MAX_RECIPE_QUANTITY,
    MAX_PINNED_ITEMS,
    MAX_PATH_LENGTH,
)


class ValidationError(Exception):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


@dataclass
class ValidationResult:
    """Result of validation operation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized_data: Optional[Any] = None


def validate_string(
    value: Any,
    field_name: str = "value",
    min_length: int = 0,
    max_length: int = 1000,
    pattern: Optional[str] = None,
    allowed_chars: Optional[str] = None,
    strip: bool = True
) -> str:
    """
    Validate and sanitize a string input.

    Args:
        value: Value to validate
        field_name: Name for error messages
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Optional regex pattern to match
        allowed_chars: Optional string of allowed characters
        strip: Whether to strip whitespace

    Returns:
        Validated and sanitized string

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if min_length > 0:
            raise ValidationError(f"{field_name} is required", field_name)
        return ""

    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field_name)

    if strip:
        value = value.strip()

    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters",
            field_name
        )

    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters",
            field_name
        )

    if pattern and not re.match(pattern, value):
        raise ValidationError(
            f"{field_name} has invalid format",
            field_name
        )

    if allowed_chars:
        invalid = set(value) - set(allowed_chars)
        if invalid:
            raise ValidationError(
                f"{field_name} contains invalid characters: {invalid}",
                field_name
            )

    return value


def validate_int(
    value: Any,
    field_name: str = "value",
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    default: Optional[int] = None
) -> int:
    """
    Validate an integer input.

    Args:
        value: Value to validate
        field_name: Name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if None

    Returns:
        Validated integer

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if default is not None:
            return default
        raise ValidationError(f"{field_name} is required", field_name)

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be an integer", field_name)

    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{field_name} must be at least {min_value}",
            field_name
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{field_name} must be at most {max_value}",
            field_name
        )

    return value


def validate_search_query(query: Any) -> str:
    """
    Validate a search query string.

    Args:
        query: Search query to validate

    Returns:
        Validated and sanitized query string

    Raises:
        ValidationError: If validation fails
    """
    return validate_string(
        query,
        field_name="query",
        min_length=0,
        max_length=MAX_QUERY_LENGTH,
        strip=True
    )


def validate_recipe_quantity(quantity: Any) -> int:
    """
    Validate a recipe quantity.

    Args:
        quantity: Quantity to validate

    Returns:
        Validated quantity

    Raises:
        ValidationError: If validation fails
    """
    return validate_int(
        quantity,
        field_name="quantity",
        min_value=1,
        max_value=MAX_RECIPE_QUANTITY,
        default=1
    )


def validate_recipe_selections(selections: Any) -> Dict[str, int]:
    """
    Validate recipe selection data from client.

    Args:
        selections: Recipe selections dict

    Returns:
        Validated selections

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(selections, dict):
        raise ValidationError("Selections must be a dictionary")

    if len(selections) > MAX_PINNED_ITEMS:
        raise ValidationError(f"Maximum {MAX_PINNED_ITEMS} recipes can be pinned")

    validated = {}
    for recipe_id, data in selections.items():
        # Validate recipe ID format - allow alphanumeric, spaces, hyphens, underscores
        # Recipe IDs are formatted as "Skill_Recipe Name_index" (e.g., "Cooking_Basic Bread_0")
        recipe_id = validate_string(
            recipe_id,
            field_name="recipe_id",
            max_length=200,
            pattern=r'^[\w\s\-\'",.()]+$'  # Allow common recipe name characters
        )

        # Extract and validate quantity
        if isinstance(data, dict):
            quantity = validate_recipe_quantity(data.get('quantity', 1))
        else:
            quantity = validate_recipe_quantity(data)

        validated[recipe_id] = quantity

    return validated


def validate_path_input(path: Any) -> str:
    """
    Validate a path input from user.

    Args:
        path: Path string to validate

    Returns:
        Validated path string

    Raises:
        ValidationError: If validation fails
    """
    path = validate_string(
        path,
        field_name="path",
        min_length=1,
        max_length=MAX_PATH_LENGTH,
        strip=True
    )

    # Check for null bytes
    if '\x00' in path:
        raise ValidationError("Path contains invalid characters", "path")

    return path


def validate_config_paths(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate configuration path data.

    Args:
        data: Configuration data with chat_log_dir and reports_dir

    Returns:
        Validated paths

    Raises:
        ValidationError: If validation fails
    """
    chat_log_dir = validate_path_input(data.get('chat_log_dir'))
    reports_dir = validate_path_input(data.get('reports_dir'))

    return {
        'chat_log_dir': chat_log_dir,
        'reports_dir': reports_dir
    }
