#!/usr/bin/env python3
"""
Launcher for Project Gorgon VIP Quest Helper
Auto-opens browser and starts Flask server
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

def main():
    """Main entry point"""
    print("="*60)
    print("Project Gorgon VIP Quest Helper")
    print("="*60)
    print("\nStarting server...")

    # Start browser opener in background thread
    url = "http://127.0.0.1:5000"
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    print(f"Opening browser to: {url}")
    print("\nPress Ctrl+C to stop the server")
    print("="*60)
    print()

    # Import and run Flask app
    try:
        from web_server import app
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
