#!/usr/bin/env bash
# Start the Project Gorgon Quest Helper

cd "$(dirname "$0")"

echo "Starting Project Gorgon Quest Helper..."
echo ""

# Enter nix-shell and run the server
nix-shell --run "python3 web_server.py"
