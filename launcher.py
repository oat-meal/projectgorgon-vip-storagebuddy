#!/usr/bin/env python3
"""
Launcher for Project Gorgon VIP Quest Helper
Auto-opens browser and starts Flask server
Automatically shuts down when browser window closes
"""

import webbrowser
import threading
import time
import sys
from pathlib import Path

def open_browser(url, delay=1.5):
    """Open browser after a short delay"""
    time.sleep(delay)
    webbrowser.open(url)

def check_browser_alive(app):
    """Monitor browser connection and shut down if disconnected"""
    import time
    from datetime import datetime, timedelta

    # Wait for initial browser connection
    time.sleep(5)

    while True:
        time.sleep(5)  # Check every 5 seconds

        # Check if we've received a heartbeat recently
        last_ping = getattr(app, 'last_heartbeat', None)
        if last_ping:
            time_since_ping = datetime.now() - last_ping
            if time_since_ping > timedelta(seconds=30):
                print("\nBrowser disconnected. Shutting down...")
                import os
                import signal
                os.kill(os.getpid(), signal.SIGINT)
                break

def main():
    """Main entry point"""
    from datetime import datetime

    print("="*60)
    print("Project Gorgon VIP Quest Helper")
    print("="*60)
    print("\nStarting server...")

    # Import Flask app before starting threads
    from web_server import app

    # Initialize heartbeat tracking
    app.last_heartbeat = datetime.now()

    # Start browser opener in background thread
    url = "http://127.0.0.1:5000"
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Start browser monitor thread
    threading.Thread(target=check_browser_alive, args=(app,), daemon=True).start()

    print(f"Opening browser to: {url}")
    print("\nServer will auto-close when you close the browser window")
    print("Or press Ctrl+C to stop manually")
    print("="*60)
    print()

    # Run Flask app
    try:
        # Disable Flask debug mode for production executable
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
