#!/usr/bin/env python3
"""
Launcher for Project Gorgon VIP Quest Helper
Auto-opens browser and starts Flask server
Automatically shuts down when browser window closes

Usage:
  launcher.py          - Normal mode (opens in browser)
  launcher.py --overlay - Overlay mode (transparent window for in-game use)
"""

import webbrowser
import threading
import time
import sys
import argparse
import socket
import logging
from pathlib import Path
from datetime import datetime

def setup_overlay_debug_logging():
    """Setup debug logging for overlay mode"""
    import platform
    import os

    # Determine user data directory
    if platform.system() == 'Windows':
        data_dir = Path(os.environ.get('LOCALAPPDATA', '~')) / 'ProjectGorgon-QuestHelper'
    elif platform.system() == 'Darwin':
        data_dir = Path('~/Library/Application Support/ProjectGorgon-QuestHelper').expanduser()
    else:
        data_dir = Path('~/.local/share/projectgorgon-questhelper').expanduser()

    data_dir.mkdir(parents=True, exist_ok=True)
    log_file = data_dir / 'overlay-debug.log'

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),  # Overwrite each time
            logging.StreamHandler(sys.stdout)  # Also print to console
        ]
    )

    logging.info("="*60)
    logging.info("Overlay Debug Log Started")
    logging.info(f"Platform: {platform.system()} {platform.release()}")
    logging.info(f"Python: {sys.version}")
    logging.info(f"Log file: {log_file}")
    logging.info("="*60)

    # Log environment variables (especially important for Linux/Wayland/Qt)
    logging.info("\n--- Environment Variables ---")
    env_vars_to_log = [
        'DISPLAY', 'WAYLAND_DISPLAY', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP',
        'QT_QPA_PLATFORM', 'QT_QPA_PLATFORMTHEME', 'QT_WAYLAND_DISABLE_WINDOWDECORATION',
        'GDK_BACKEND', 'GTK_THEME', 'DESKTOP_SESSION',
        'PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH'
    ]
    for var in env_vars_to_log:
        value = os.environ.get(var, '<not set>')
        logging.info(f"  {var}: {value}")

    # Log Python library versions
    logging.info("\n--- Python Libraries ---")
    try:
        import webview
        logging.info(f"  pywebview: {webview.__version__ if hasattr(webview, '__version__') else 'unknown'}")
    except ImportError:
        logging.info("  pywebview: NOT INSTALLED")

    try:
        import flask
        logging.info(f"  flask: {flask.__version__ if hasattr(flask, '__version__') else 'unknown'}")
    except ImportError:
        logging.info("  flask: NOT INSTALLED")

    # Linux-specific library detection
    if platform.system() == 'Linux':
        logging.info("\n--- Linux Display Libraries ---")

        # Check GTK
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
            gtk_version = f"{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}"
            logging.info(f"  GTK3: {gtk_version}")
        except Exception as e:
            logging.info(f"  GTK3: Error - {e}")

        # Check WebKit2GTK
        try:
            import gi
            gi.require_version('WebKit2', '4.1')
            from gi.repository import WebKit2
            webkit_version = WebKit2.get_major_version(), WebKit2.get_minor_version(), WebKit2.get_micro_version()
            logging.info(f"  WebKit2GTK: {'.'.join(map(str, webkit_version))}")
        except Exception as e:
            logging.info(f"  WebKit2GTK: Error - {e}")

        # Check Qt availability
        try:
            from PyQt5.QtCore import QT_VERSION_STR
            logging.info(f"  Qt5 (PyQt5): {QT_VERSION_STR}")
        except ImportError:
            logging.info("  Qt5 (PyQt5): NOT INSTALLED")

        try:
            from PyQt6.QtCore import QT_VERSION_STR
            logging.info(f"  Qt6 (PyQt6): {QT_VERSION_STR}")
        except ImportError:
            logging.info("  Qt6 (PyQt6): NOT INSTALLED")

        try:
            import PySide6
            logging.info(f"  Qt6 (PySide6): {PySide6.__version__}")
        except ImportError:
            logging.info("  Qt6 (PySide6): NOT INSTALLED")

    logging.info("="*60 + "\n")

    return log_file

def is_port_in_use(port, host='127.0.0.1'):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            logging.debug(f"Port {port} is available")
            return False
        except OSError as e:
            logging.debug(f"Port {port} is in use: {e}")
            return True

def open_browser(url, delay=1.5):
    """Open browser after a short delay"""
    time.sleep(delay)
    webbrowser.open(url)

def open_overlay_window(url):
    """Open overlay window using pywebview"""
    logging.info("Opening overlay window...")

    try:
        import webview
        logging.info(f"pywebview imported successfully (version: {webview.__version__ if hasattr(webview, '__version__') else 'unknown'})")

        # Detect which backend will be used
        import platform
        if platform.system() == 'Linux':
            logging.info("\n--- pywebview Backend Detection (Linux) ---")

            # Check for available backends
            backends_available = []

            # GTK backend
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                gi.require_version('WebKit2', '4.1')
                backends_available.append("gtk")
                logging.info("  GTK backend: AVAILABLE")
            except Exception as e:
                logging.info(f"  GTK backend: UNAVAILABLE ({e})")

            # Qt backend (PyQt5)
            try:
                from PyQt5 import QtCore
                backends_available.append("qt (PyQt5)")
                logging.info("  Qt backend (PyQt5): AVAILABLE")
            except ImportError as e:
                logging.info(f"  Qt backend (PyQt5): UNAVAILABLE ({e})")

            # Qt backend (PyQt6)
            try:
                from PyQt6 import QtCore
                backends_available.append("qt (PyQt6)")
                logging.info("  Qt backend (PyQt6): AVAILABLE")
            except ImportError as e:
                logging.info(f"  Qt backend (PyQt6): UNAVAILABLE ({e})")

            # Qt backend (PySide6)
            try:
                from PySide6 import QtCore
                backends_available.append("qt (PySide6)")
                logging.info("  Qt backend (PySide6): AVAILABLE")
            except ImportError as e:
                logging.info(f"  Qt backend (PySide6): UNAVAILABLE ({e})")

            logging.info(f"\n  Available backends: {backends_available if backends_available else 'NONE'}")
            logging.info("  pywebview will automatically choose the first available backend")
            logging.info("  Priority order: GTK > Qt (any variant)")
            logging.info("="*60 + "\n")

    except ImportError as e:
        logging.error(f"pywebview import failed: {e}")
        print("ERROR: pywebview not installed. Overlay mode requires pywebview.")
        print("Install with: pip install pywebview")
        sys.exit(1)

    # Wait for server to be ready
    logging.info(f"Checking if server is ready at {url}/api/version...")
    import urllib.request
    for i in range(10):
        try:
            response = urllib.request.urlopen(f"{url}/api/version", timeout=1)
            data = response.read().decode('utf-8')
            logging.info(f"Server ready! Response: {data}")
            break
        except Exception as e:
            logging.debug(f"Server not ready (attempt {i+1}/10): {e}")
            if i < 9:
                time.sleep(0.5)
            else:
                logging.error("Server failed to start after 10 attempts")
                print("ERROR: Server failed to start")
                return

    print("Server ready!")
    print("\nLaunching overlay window...")
    print("Controls:")
    print("  - Click and drag to move the overlay")
    print("  - Use dropdown to switch between Ready/Buyable/Active views")
    print("  - Close window to exit")
    print("=" * 60)
    print()

    # Create overlay window
    logging.info("Creating pywebview window...")
    logging.info(f"Window URL: {url}/overlay")
    logging.info(f"Window parameters: width=320, height=500, frameless=True, on_top=True, transparent=True")

    try:
        window = webview.create_window(
            'Quest Tracker Overlay',
            f'{url}/overlay',
            width=320,
            height=500,
            resizable=True,
            frameless=True,
            on_top=True,
            transparent=True,
            background_color='#000000'
        )
        logging.info("Window created successfully")
        logging.info(f"Window object: {window}")
        logging.info(f"Window type: {type(window)}")
    except Exception as e:
        logging.error(f"Failed to create window: {e}", exc_info=True)
        raise

    # Start the webview (blocks until window is closed)
    logging.info("Starting webview...")
    logging.info("About to call webview.start() - this will initialize the GUI backend")

    try:
        # Determine which backend to use
        import platform
        gui_backend = None
        if platform.system() == 'Linux':
            # Force GTK backend on Linux to avoid Qt/PySide6 segfault issues
            # GTK with WebKit2GTK is more stable on Linux than Qt backends
            gui_backend = 'gtk'
            logging.info(f"Forcing GUI backend: {gui_backend}")
            logging.info("Reason: GTK/WebKit2GTK is more stable than Qt on Linux")

        if gui_backend:
            logging.info(f"Calling webview.start(gui='{gui_backend}', debug=False)...")
            webview.start(gui=gui_backend, debug=False)
        else:
            logging.info("Calling webview.start(debug=False) with auto-detection...")
            webview.start(debug=False)

        logging.info("Webview closed normally")
    except Exception as e:
        logging.error(f"Webview error: {e}", exc_info=True)
        logging.error("Webview crashed or failed to start")
        logging.error("If this is a segmentation fault, check the system logs for more details")
        raise

def check_browser_alive(app):
    """Monitor browser connection and shut down if disconnected"""
    import time
    from datetime import datetime, timedelta

    # Wait for initial browser connection
    time.sleep(3)

    while True:
        time.sleep(1)  # Check every 1 second for fast shutdown

        # Check if we've received a heartbeat recently
        last_ping = getattr(app, 'last_heartbeat', None)
        if last_ping:
            time_since_ping = datetime.now() - last_ping
            if time_since_ping > timedelta(seconds=6):  # 6 second timeout
                print("\nBrowser disconnected. Shutting down...")
                import os
                import signal
                os.kill(os.getpid(), signal.SIGINT)
                break

def main():
    """Main entry point"""
    from datetime import datetime

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Project Gorgon VIP Quest Helper')
    parser.add_argument('--overlay', action='store_true',
                       help='Launch in overlay mode (transparent window for in-game use)')
    args = parser.parse_args()

    print("="*60)
    print("Project Gorgon VIP Quest Helper")
    if args.overlay:
        print("OVERLAY MODE")
    print("="*60)
    print("\nStarting server...")

    # Import Flask app before starting threads
    from web_server import app

    # Initialize heartbeat tracking (used by normal mode only)
    app.last_heartbeat = datetime.now()

    url = "http://127.0.0.1:5000"

    if args.overlay:
        # Setup debug logging for overlay mode
        log_file = setup_overlay_debug_logging()
        print(f"\nDebug logging enabled: {log_file}")
        logging.info("Entering overlay mode")

        # Overlay mode: Check if server is already running
        logging.info("Checking if port 5000 is in use...")
        server_already_running = is_port_in_use(5000)

        if server_already_running:
            logging.info("Server detected on port 5000 - connecting to existing server")
            print("Detected existing server on port 5000")
            print("Connecting to existing server...")
        else:
            logging.info("No server detected - starting new Flask server")
            print("No existing server detected")
            print("Starting Flask server in background...")

            # Start server in background
            def start_server():
                logging.info("Flask server thread started")
                try:
                    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False, threaded=True)
                except Exception as e:
                    logging.error(f"Flask server error: {e}")

            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            logging.info("Flask server thread started in background")

        # Open overlay window (blocks until closed)
        try:
            open_overlay_window(url)
        except Exception as e:
            logging.error(f"Error opening overlay window: {e}", exc_info=True)
            print(f"\nERROR: {e}")
            print(f"See debug log for details: {log_file}")

        logging.info("Overlay window closed")
        print("\nOverlay closed. Shutting down...")
        print(f"Debug log saved to: {log_file}")
        sys.exit(0)

    else:
        # Normal mode: Open browser and monitor for shutdown
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()
        threading.Thread(target=check_browser_alive, args=(app,), daemon=True).start()

        print(f"Opening browser to: {url}")
        print("\nServer will auto-close when you close the browser window")
        print("Or press Ctrl+C to stop manually")
        print("="*60)
        print()

        # Run Flask app
        try:
            app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
        except KeyboardInterrupt:
            print("\n\nQuest Helper stopped. Thank you!")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {e}")
            print("\nPress Enter to exit...")
            input()
            sys.exit(1)

if __name__ == '__main__':
    main()
