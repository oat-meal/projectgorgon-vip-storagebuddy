#!/usr/bin/env python3
"""
Build standalone executable for Project Gorgon VIP StorageBuddy
Uses PyInstaller to bundle Python, Flask, and all dependencies
"""

import subprocess
import sys
import platform
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller is installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
            print("✓ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install PyInstaller")
            return False

def build_executable():
    """Build the executable using PyInstaller"""

    # Platform-specific settings
    system = platform.system()
    icon_file = None  # TODO: Add icon file if desired

    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--name=StorageBuddy',
        '--onefile',  # Single executable
        '--windowed',  # No console window (comment out for debugging)
        '--add-data=templates:templates',  # Include templates
        '--add-data=static:static',  # Include static files if any
        '--add-data=recipes.json:.',  # Include recipes data
        '--hidden-import=flask',
        '--hidden-import=jinja2',
        '--collect-all=flask',
        'launcher.py'  # Entry point
    ]

    if icon_file and Path(icon_file).exists():
        cmd.extend(['--icon', icon_file])

    print(f"\nBuilding executable for {system}...")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        subprocess.check_call(cmd)
        print("\n" + "="*60)
        print("✓ Build successful!")
        print("="*60)

        if system == 'Windows':
            exe_path = Path('dist') / 'StorageBuddy.exe'
        else:
            exe_path = Path('dist') / 'StorageBuddy'

        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\nExecutable created: {exe_path}")
            print(f"Size: {size_mb:.1f} MB")
            print(f"\nUsers can now run this file directly!")
            print("No Python installation required.")

        return True

    except subprocess.CalledProcessError as e:
        print("\n✗ Build failed!")
        print(f"Error: {e}")
        return False

def main():
    print("="*60)
    print("Project Gorgon VIP StorageBuddy - Executable Builder")
    print("="*60)
    print()

    if not install_pyinstaller():
        sys.exit(1)

    if not build_executable():
        sys.exit(1)

    print("\n" + "="*60)
    print("Next steps:")
    print("="*60)
    print("1. Test the executable in dist/StorageBuddy")
    print("2. Upload to GitHub Releases for distribution")
    print("3. Users download and double-click to run!")
    print()

if __name__ == '__main__':
    main()
