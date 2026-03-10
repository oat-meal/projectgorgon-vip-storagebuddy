"""
Configuration API routes
"""

import platform
import logging
from pathlib import Path
from flask import Blueprint, request

from config import get_config
from version import __version__
from ..utils.responses import api_response, api_error
from ..utils.validation import validate_config_paths, ValidationError
from ..utils.security import validate_path, SecurityError
from .decorators import reinitialize_tracker

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__)


@config_bp.route('/config_status')
def get_config_status():
    """Get configuration status for troubleshooting"""
    config = get_config()
    return api_response(data=config.get_status())


@config_bp.route('/auto_detect', methods=['POST'])
def auto_detect_paths():
    """Try to auto-detect game data paths"""
    logger.info("Auto-detect requested")
    logger.info(f"Platform: {platform.system()}")

    config = get_config()
    detected = config._auto_detect_game_data()

    if detected:
        logger.info(f"Auto-detect succeeded: {detected['detected_path']}")

        # Save the detected paths
        config.config.update(detected)
        config._save_config()

        # Reinitialize tracker with new paths
        reinitialize_tracker()

        # Get stats about what was found
        chat_dir = Path(detected['chat_log_dir'])
        reports_dir = Path(detected['reports_dir'])

        chat_log_count = len(list(chat_dir.glob('Chat-*.log')))
        character_files_count = len(list(reports_dir.glob('Character_*.json')))

        logger.info(f"  Chat logs: {chat_dir} ({chat_log_count} files)")
        logger.info(f"  Reports: {reports_dir} ({character_files_count} files)")

        return api_response(data={
            'detected_path': detected['detected_path'],
            'chat_log_dir': str(chat_dir),
            'reports_dir': str(reports_dir),
            'chat_log_count': chat_log_count,
            'character_files_count': character_files_count
        }, message="Game data detected successfully")
    else:
        logger.warning("Auto-detect failed: Could not find Project Gorgon game data")
        return api_error(
            "Could not find Project Gorgon game data in common locations",
            code="NOT_FOUND",
            status_code=404
        )


@config_bp.route('/save_config', methods=['POST'])
def save_configuration():
    """Save custom configuration from user"""
    data = request.get_json()

    if not data:
        return api_error("No data provided", status_code=400)

    try:
        # Validate input
        validated = validate_config_paths(data)

        chat_log_dir = validated['chat_log_dir']
        reports_dir = validated['reports_dir']

        # Validate paths exist and are directories
        try:
            validate_path(chat_log_dir, must_exist=True, must_be_dir=True)
            validate_path(reports_dir, must_exist=True, must_be_dir=True)
        except SecurityError as e:
            return api_error(str(e), code="INVALID_PATH", status_code=400)

        # Save configuration
        config = get_config()
        config.set_custom_paths(chat_log_dir, reports_dir)

        # Reinitialize tracker with new paths
        reinitialize_tracker()

        return api_response(message="Configuration saved successfully")

    except ValidationError as e:
        return api_error(e.message, code="VALIDATION_ERROR", status_code=400)
    except ValueError as e:
        return api_error(str(e), code="INVALID_CONFIG", status_code=400)


@config_bp.route('/version')
def get_version():
    """Get application version"""
    import sys
    config = get_config()

    return api_response(data={
        'version': __version__,
        'frozen': getattr(sys, 'frozen', False),
        'log_file': str(config.get_base_dir() / 'storagebuddy.log')
    })


@config_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Browser heartbeat to detect when window closes"""
    from datetime import datetime
    from flask import current_app

    current_app.last_heartbeat = datetime.now()
    return api_response(data={'status': 'ok'})
