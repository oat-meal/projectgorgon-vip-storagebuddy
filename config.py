#!/usr/bin/env python3
"""
Configuration management for Project Gorgon VIP Quest Helper
Handles path detection across Windows, Linux, and Proton
"""

import json
import platform
from pathlib import Path
from typing import Optional, Dict, List


class Config:
    """Manages configuration and path detection"""

    def __init__(self, config_file: Optional[Path] = None):
        if config_file is None:
            config_file = Path(__file__).parent / 'config.json'

        self.config_file = config_file
        self.config = self._load_config()
        self._detect_paths()

    def _load_config(self) -> Dict:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_config(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _detect_paths(self):
        """Auto-detect game data paths if not configured"""
        # If paths are already configured and valid, use them
        if self._validate_configured_paths():
            return

        # Try to auto-detect
        detected = self._auto_detect_game_data()
        if detected:
            self.config.update(detected)
            self._save_config()

    def _validate_configured_paths(self) -> bool:
        """Check if configured paths exist and are valid"""
        chat_log_dir = self.config.get('chat_log_dir')
        reports_dir = self.config.get('reports_dir')

        if not chat_log_dir or not reports_dir:
            return False

        chat_path = Path(chat_log_dir)
        reports_path = Path(reports_dir)

        return chat_path.exists() and reports_path.exists()

    def _auto_detect_game_data(self) -> Optional[Dict]:
        """Try to auto-detect game data location"""
        search_paths = self._get_search_paths()

        for base_path in search_paths:
            pg_data = base_path / 'Project Gorgon Data'
            if pg_data.exists():
                chat_logs = pg_data / 'ChatLogs'
                reports = pg_data / 'Reports'

                if chat_logs.exists() and reports.exists():
                    return {
                        'chat_log_dir': str(chat_logs),
                        'reports_dir': str(reports),
                        'auto_detected': True,
                        'detected_path': str(pg_data)
                    }

        return None

    def _get_search_paths(self) -> List[Path]:
        """Get list of paths to search for game data"""
        search_paths = []
        home = Path.home()

        # Native Documents folder (Windows and Linux)
        search_paths.append(home / 'Documents')

        # Proton/Wine paths (Linux with Steam)
        # Common Steam library locations
        steam_paths = [
            home / '.steam' / 'steam',
            home / '.local' / 'share' / 'Steam',
        ]

        # Project Gorgon Steam App ID: 342940
        app_id = '342940'

        for steam_path in steam_paths:
            if steam_path.exists():
                # Check compatdata for Proton prefix
                compatdata = steam_path / 'steamapps' / 'compatdata' / app_id / 'pfx' / 'drive_c' / 'users' / 'steamuser' / 'Documents'
                if compatdata.exists():
                    search_paths.append(compatdata)

                # Also check common name (some Proton versions use 'Public')
                compatdata_public = steam_path / 'steamapps' / 'compatdata' / app_id / 'pfx' / 'drive_c' / 'users' / 'Public' / 'Documents'
                if compatdata_public.exists():
                    search_paths.append(compatdata_public)

        # Windows-specific paths (if running on Windows)
        if platform.system() == 'Windows':
            # Already covered by home / 'Documents' but let's be explicit
            import os
            docs = Path(os.path.expandvars('%USERPROFILE%')) / 'Documents'
            if docs not in search_paths:
                search_paths.append(docs)

        return search_paths

    def get_chat_log_dir(self) -> Optional[Path]:
        """Get chat log directory path"""
        path_str = self.config.get('chat_log_dir')
        if path_str:
            path = Path(path_str)
            if path.exists():
                return path
        return None

    def get_reports_dir(self) -> Optional[Path]:
        """Get reports directory path"""
        path_str = self.config.get('reports_dir')
        if path_str:
            path = Path(path_str)
            if path.exists():
                return path
        return None

    def get_base_dir(self) -> Path:
        """Get base directory for quest tracker data"""
        # Use platform-specific user data directory
        if 'base_dir' in self.config:
            return Path(self.config['base_dir'])

        # Determine platform-specific data directory
        if platform.system() == 'Windows':
            # Windows: AppData\Local\ProjectGorgonQuestHelper
            base_dir = Path.home() / 'AppData' / 'Local' / 'ProjectGorgonQuestHelper'
        else:
            # Linux/Mac: ~/.local/share/projectgorgon-questhelper
            base_dir = Path.home() / '.local' / 'share' / 'projectgorgon-questhelper'

        # Create directory if it doesn't exist
        base_dir.mkdir(parents=True, exist_ok=True)

        return base_dir

    def set_custom_paths(self, chat_log_dir: str, reports_dir: str):
        """Set custom paths for game data"""
        chat_path = Path(chat_log_dir)
        reports_path = Path(reports_dir)

        if not chat_path.exists():
            raise ValueError(f"Chat log directory does not exist: {chat_log_dir}")
        if not reports_path.exists():
            raise ValueError(f"Reports directory does not exist: {reports_dir}")

        self.config['chat_log_dir'] = str(chat_path)
        self.config['reports_dir'] = str(reports_path)
        self.config['auto_detected'] = False
        self._save_config()

    def get_bundled_resource_dir(self) -> Optional[Path]:
        """Get bundled resource directory if running as PyInstaller executable"""
        import sys
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            return Path(sys._MEIPASS)
        else:
            # Running as normal Python script - check if files exist locally
            script_dir = Path(__file__).parent
            if (script_dir / 'quests.json').exists() and (script_dir / 'items.json').exists():
                return script_dir
        return None

    def get_status(self) -> Dict:
        """Get configuration status for troubleshooting"""
        chat_dir = self.get_chat_log_dir()
        reports_dir = self.get_reports_dir()

        status = {
            'configured': bool(chat_dir and reports_dir),
            'auto_detected': self.config.get('auto_detected', False),
            'platform': platform.system(),
            'chat_log_dir': str(chat_dir) if chat_dir else None,
            'reports_dir': str(reports_dir) if reports_dir else None,
            'chat_log_exists': chat_dir.exists() if chat_dir else False,
            'reports_exists': reports_dir.exists() if reports_dir else False,
        }

        # Count files if directories exist
        if chat_dir and chat_dir.exists():
            status['chat_log_count'] = len(list(chat_dir.glob('Chat-*.log')))
        if reports_dir and reports_dir.exists():
            status['character_files_count'] = len(list(reports_dir.glob('Character_*.json')))

        return status


def get_config() -> Config:
    """Get or create global config instance"""
    global _config_instance
    if '_config_instance' not in globals():
        _config_instance = Config()
    return _config_instance
