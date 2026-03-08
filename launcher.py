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
from pathlib import Path

def open_browser(url, delay=1.5):
    """Open browser after a short delay"""
    time.sleep(delay)
    webbrowser.open(url)

def open_overlay_window(url):
    """Open overlay window using pywebview"""
    try:
        import webview
    except ImportError:
        print("ERROR: pywebview not installed. Overlay mode requires pywebview.")
        print("Install with: pip install pywebview")
        sys.exit(1)

    # Wait for server to be ready
    import urllib.request
    for i in range(10):
        try:
            urllib.request.urlopen(f"{url}/api/version", timeout=1)
            break
        except:
            if i < 9:
                time.sleep(0.5)
            else:
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
    window = webview.create_window(
        'Quest Tracker Overlay',
        f'{url}/overlay',
        width=320,
        height=500,
        resizable=True,
        frameless=True,
        on_top=True,
        transparent=True,
        background_color='#00000000'
    )

    # Start the webview (blocks until window is closed)
    webview.start(debug=False)

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
        # Overlay mode: Start server in background and open pywebview window
        def start_server():
            app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False, threaded=True)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        # Open overlay window (blocks until closed)
        open_overlay_window(url)

        print("\nOverlay closed. Shutting down...")
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
