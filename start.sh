#!/usr/bin/env bash
# Start the Project Gorgon Quest Tracker

cd "$(dirname "$0")"

echo "Starting Project Gorgon Quest Tracker..."
echo ""

# Enter nix-shell and run the server
nix-shell --run "python3 web_server.py"
