"""
Standardized API response utilities
"""

from typing import Any, Optional, Dict
from flask import jsonify
from datetime import datetime

from version import __version__


def api_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
):
    """
    Create a standardized successful API response.

    Args:
        data: Response data (dict, list, or primitive)
        message: Optional success message
        meta: Optional metadata
        status_code: HTTP status code (default 200)

    Returns:
        Flask JSON response tuple (response, status_code)

    Response format:
    {
        "success": true,
        "data": {...},
        "message": "Optional message",
        "meta": {
            "timestamp": "2026-03-10T17:30:00Z",
            "version": "0.6.2"
        }
    }

    Frontend should access data via: response.data.quests, response.data.items, etc.
    """
    response = {
        'success': True,
        'data': data,
    }

    if message:
        response['message'] = message

    # Add metadata
    response['meta'] = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': __version__,
        **(meta or {})
    }

    return jsonify(response), status_code


def api_error(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
):
    """
    Create a standardized error API response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code (e.g., "NOT_FOUND", "VALIDATION_ERROR")
        details: Additional error details
        status_code: HTTP status code (default 400)

    Returns:
        Flask JSON response tuple (response, status_code)

    Example response format:
    {
        "success": false,
        "error": {
            "code": "NOT_FOUND",
            "message": "Quest not found",
            "details": {"quest_id": "abc123"}
        },
        "meta": {
            "timestamp": "2026-03-10T17:30:00Z",
            "version": "0.6.1"
        }
    }
    """
    response = {
        'success': False,
        'error': {
            'code': code or _status_to_code(status_code),
            'message': message,
        },
        'meta': {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': __version__,
        }
    }

    if details:
        response['error']['details'] = details

    return jsonify(response), status_code


def _status_to_code(status_code: int) -> str:
    """Convert HTTP status code to error code string"""
    codes = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        409: 'CONFLICT',
        422: 'VALIDATION_ERROR',
        429: 'RATE_LIMITED',
        500: 'INTERNAL_ERROR',
        503: 'SERVICE_UNAVAILABLE',
    }
    return codes.get(status_code, 'ERROR')


# Common error responses
def not_found(message: str = "Resource not found", details: Optional[Dict] = None):
    """404 Not Found response"""
    return api_error(message, code="NOT_FOUND", details=details, status_code=404)


def bad_request(message: str = "Invalid request", details: Optional[Dict] = None):
    """400 Bad Request response"""
    return api_error(message, code="BAD_REQUEST", details=details, status_code=400)


def validation_error(message: str, details: Optional[Dict] = None):
    """422 Validation Error response"""
    return api_error(message, code="VALIDATION_ERROR", details=details, status_code=422)


def internal_error(message: str = "Internal server error"):
    """500 Internal Server Error response (sanitized for production)"""
    return api_error(message, code="INTERNAL_ERROR", status_code=500)


def service_unavailable(message: str = "Service temporarily unavailable"):
    """503 Service Unavailable response"""
    return api_error(message, code="SERVICE_UNAVAILABLE", status_code=503)


def not_configured():
    """503 response for unconfigured application"""
    return api_error(
        "Application not configured. Please complete setup at /setup",
        code="NOT_CONFIGURED",
        status_code=503
    )
