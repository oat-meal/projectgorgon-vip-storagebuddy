"""
Route blueprints for StorageBuddy
"""

from flask import Flask


def register_routes(app: Flask) -> None:
    """Register all route blueprints with the app"""
    from .main import main_bp
    from .quests import quests_bp
    from .crafting import crafting_bp
    from .config_routes import config_bp
    from .data import data_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(quests_bp, url_prefix='/api')
    app.register_blueprint(crafting_bp, url_prefix='/api')
    app.register_blueprint(config_bp, url_prefix='/api')
    app.register_blueprint(data_bp, url_prefix='/api')
