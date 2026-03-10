"""
Main routes (pages, not API)
"""

from flask import Blueprint, render_template, redirect

from config import get_config
from version import __version__

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main page - redirect to setup if not configured"""
    config = get_config()
    if not config.get_status()['configured']:
        return redirect('/setup')
    return render_template('index.html', version=__version__)


@main_bp.route('/setup')
def setup():
    """Setup wizard page"""
    return render_template('setup.html')


@main_bp.route('/overlay')
def overlay():
    """Overlay mode for in-game display"""
    return render_template('overlay.html', version=__version__)
