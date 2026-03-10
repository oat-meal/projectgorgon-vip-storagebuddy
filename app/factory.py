"""
Flask application factory with security middleware
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify, g
from flask_cors import CORS

from version import __version__
from config import get_config
from .utils.security import sanitize_log_data, set_secure_file_permissions
from .utils.responses import api_error, internal_error
from .utils.rate_limit import apply_global_rate_limit

logger = logging.getLogger(__name__)


def create_app(debug: bool = False) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        debug: Enable debug mode

    Returns:
        Configured Flask application
    """
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Configuration
    app.config['DEBUG'] = debug
    app.config['JSON_SORT_KEYS'] = False

    # Initialize config
    config = get_config()

    # Set up logging
    _setup_logging(app, config, debug)

    # Configure CORS (restrictive by default)
    _configure_cors(app)

    # Add security headers
    _add_security_headers(app)

    # Add request logging (with sanitization)
    _add_request_logging(app, debug)

    # Add error handlers
    _add_error_handlers(app, debug)

    # Apply rate limiting to API endpoints
    apply_global_rate_limit(app)

    # Store config in app context
    app.config['STORAGE_BUDDY_CONFIG'] = config

    # Register blueprints
    _register_blueprints(app)

    logger.info(f"StorageBuddy v{__version__} initialized")
    logger.info(f"Debug mode: {debug}")

    return app


def _setup_logging(app: Flask, config, debug: bool) -> None:
    """Configure application logging"""
    base_dir = config.get_base_dir()
    log_file = base_dir / 'storagebuddy.log'

    log_level = logging.DEBUG if debug else logging.INFO

    # Create log file with secure permissions
    if not log_file.exists():
        log_file.touch()
    set_secure_file_permissions(log_file, mode=0o600)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger.info("=" * 80)
    logger.info(f"StorageBuddy Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    logger.info(f"Version: {__version__}")
    logger.info(f"Log level: {'DEBUG' if debug else 'INFO'}")
    logger.info(f"Log file: {log_file}")


def _configure_cors(app: Flask) -> None:
    """
    Configure CORS with restrictive settings.

    Only allows requests from:
    - Same origin (no CORS needed)
    - Localhost variations
    """
    # For a local-only app, we can be restrictive
    # Only allow localhost origins
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://127.0.0.1:5000",
                "http://localhost:5000",
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })


def _add_security_headers(app: Flask) -> None:
    """Add security headers to all responses"""

    @app.after_request
    def add_security_headers(response):
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Needed for inline scripts in templates
            "style-src 'self' 'unsafe-inline'; "   # Needed for inline styles
            "img-src 'self' data:; "               # Allow data URIs for images
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # XSS Protection (legacy, but doesn't hurt)
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response


def _add_request_logging(app: Flask, debug: bool) -> None:
    """Add request/response logging with data sanitization"""

    @app.before_request
    def log_request():
        # Log request details (sanitized)
        log_data = {
            'method': request.method,
            'path': request.path,
        }

        if request.args and debug:
            log_data['query'] = sanitize_log_data(dict(request.args))

        if request.is_json and debug:
            log_data['body'] = sanitize_log_data(request.get_json(silent=True))

        logger.info(f">>> {log_data['method']} {log_data['path']}")
        if debug and (request.args or request.is_json):
            logger.debug(f"    Request data: {log_data}")

    @app.after_request
    def log_response(response):
        logger.info(f"<<< {response.status_code} {request.method} {request.path}")
        return response


def _add_error_handlers(app: Flask, debug: bool) -> None:
    """Add error handlers with appropriate detail levels"""

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log full error details
        logger.error(f"Unhandled exception in {request.method} {request.path}")
        logger.error(f"Exception: {type(e).__name__}: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")

        # Return appropriate error response
        if request.path.startswith('/api/'):
            if debug:
                # In debug mode, include more details
                return api_error(
                    message=str(e),
                    code=type(e).__name__,
                    details={'traceback': traceback.format_exc().split('\n')},
                    status_code=500
                )
            else:
                # In production, return sanitized error
                return internal_error("An unexpected error occurred")

        # For non-API routes
        if debug:
            return f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>", 500
        else:
            return "<h1>Internal Server Error</h1><p>An unexpected error occurred.</p>", 500

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith('/api/'):
            return api_error("Resource not found", code="NOT_FOUND", status_code=404)
        return "<h1>Page Not Found</h1>", 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        if request.path.startswith('/api/'):
            return api_error(
                "Method not allowed",
                code="METHOD_NOT_ALLOWED",
                status_code=405
            )
        return "<h1>Method Not Allowed</h1>", 405


def _register_blueprints(app: Flask) -> None:
    """Register route blueprints"""
    # Import here to avoid circular imports
    from .routes import register_routes
    register_routes(app)
