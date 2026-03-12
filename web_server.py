#!/usr/bin/env python3
"""
Project Gorgon VIP StorageBuddy - Web Server

This module provides the Flask web server for the StorageBuddy application.
It uses a modular architecture with separate routes, services, and utilities.

Usage:
    python web_server.py [--debug]

The server will start on http://127.0.0.1:5000
"""

import sys
import argparse
import logging
import platform
from pathlib import Path
from datetime import datetime

# Ensure the app package is importable
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, jsonify, request
from config import get_config
from version import __version__
from data_updater import ensure_quest_data
from app.utils.paths import get_bundled_path

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Project Gorgon VIP StorageBuddy')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args, unknown = parser.parse_known_args()


def create_app(debug: bool = False) -> Flask:
    """
    Create and configure the Flask application.

    This is the application factory that sets up all routes, middleware,
    and configuration for the StorageBuddy web server.
    """
    # Import the app factory
    try:
        from app.factory import create_app as factory_create_app
        return factory_create_app(debug=debug)
    except ImportError as e:
        # Fall back to creating a basic app if the modular structure isn't available
        logging.warning(f"Could not import app factory: {e}")
        return _create_fallback_app(debug)


def _create_fallback_app(debug: bool = False) -> Flask:
    """Create a basic Flask app as fallback"""
    from flask_cors import CORS

    app = Flask(__name__)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://127.0.0.1:5000", "http://localhost:5000"]
        }
    })

    config = get_config()

    @app.route('/')
    def index():
        if not config.get_status()['configured']:
            from flask import redirect
            return redirect('/setup')
        return render_template('index.html', version=__version__)

    @app.route('/setup')
    def setup():
        return render_template('setup.html')

    @app.route('/overlay')
    def overlay():
        return render_template('overlay.html', version=__version__)

    @app.route('/api/version')
    def version():
        return jsonify({
            'success': True,
            'data': {
                'version': __version__,
                'frozen': getattr(sys, 'frozen', False)
            }
        })

    @app.route('/api/config_status')
    def config_status():
        return jsonify({
            'success': True,
            'data': config.get_status()
        })

    return app


# Initialize configuration and ensure game data
config = get_config()
base_dir = config.get_base_dir()

# Set up basic logging before app creation
log_level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info(f"StorageBuddy v{__version__} starting...")
logger.info("=" * 80)
logger.info(f"Platform: {platform.system()} {platform.release()}")
logger.info(f"Python: {sys.version}")
logger.info(f"Debug mode: {args.debug}")

# Ensure quest data files exist
bundled_dir = config.get_bundled_resource_dir()
if not ensure_quest_data(base_dir, bundled_dir):
    logger.warning("Failed to obtain game data files")
else:
    logger.info(f"Game data loaded from {base_dir}")

# Create the application
app = create_app(debug=args.debug)

# Store some attributes for launcher.py compatibility
app.last_heartbeat = datetime.now()


# Add routes that need to be at module level for compatibility
# (These are handled by blueprints in the new architecture, but we add them here
# as fallbacks for any code that imports directly from web_server)

@app.route('/recipes.json')
def get_recipes_compat():
    """Serve recipes.json file (compatibility route)"""
    try:
        recipes_file = get_bundled_path('recipes.json')
        if not recipes_file.exists():
            return jsonify({'error': 'Recipes file not found'}), 404
        with open(recipes_file, 'r', encoding='utf-8') as f:
            import json
            recipes = json.load(f)
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"Error loading recipes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/launch_overlay', methods=['POST'])
def launch_overlay():
    """Launch overlay mode in a separate process"""
    import subprocess
    import os

    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            if platform.system() == 'Windows':
                subprocess.Popen([exe_path, '--overlay'],
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([exe_path, '--overlay'])
        else:
            script_path = Path(__file__).parent / 'launcher.py'
            project_root = Path(__file__).parent

            if (project_root / 'shell.nix').exists() or os.environ.get('IN_NIX_SHELL'):
                subprocess.Popen(
                    ['nix-shell', '--run', f'python3 -B {script_path} --overlay'],
                    cwd=str(project_root)
                )
            else:
                subprocess.Popen([sys.executable, '-B', str(script_path), '--overlay'])

        return jsonify({
            'success': True,
            'data': {'message': 'Overlay launched'}
        })
    except Exception as e:
        logger.error(f"Error launching overlay: {e}")
        return jsonify({
            'success': False,
            'error': {'message': str(e)}
        }), 500


if __name__ == '__main__':
    app.run(debug=args.debug, host='127.0.0.1', port=5000)
