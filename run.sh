#!/bin/bash

# ==============================================================================
#  One-Click Start Script (macOS) - Single Virtual Environment Version
# ==============================================================================
# This script opens two new Terminal windows to run the server (backend) and
# the client (frontend).
#
# Prerequisites:
# 1. You have already followed the setup steps in the README, creating a single
#    '.venv' virtual environment in the root and installing all requirements.
# 2. You have made this script executable with: chmod +x start_mac.sh
# ==============================================================================

echo "🚀 Starting FastAPI Server and PyQt6 Client..."

# Get the absolute path of the directory where the script is located
BASE_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

# --- Define Commands ---

# Command to activate the root venv, then cd into the server directory and run uvicorn
SERVER_CMD="source '$BASE_DIR/.venv/bin/activate' && \
             cd '$BASE_DIR/server' && \
             echo '--- 🐍 Starting Backend Server ---' && \
             uvicorn main:app --reload"

# Command to activate the root venv, then cd into the client directory and run the Python app
CLIENT_CMD="source '$BASE_DIR/.venv/bin/activate' && \
              cd '$BASE_DIR/client' && \
              echo '--- 🖼️ Starting Frontend Client ---' && \
              python main.py"


# --- Execute in New Terminal Windows using AppleScript ---

# Open a new terminal window for the server
osascript <<EOD
tell application "Terminal"
    do script "$SERVER_CMD"
end tell
EOD

# Give it a moment to launch
sleep 1

# Open another new terminal window for the client
osascript <<EOD
tell application "Terminal"
    do script "$CLIENT_CMD"
end tell
EOD

echo "✅ Both services have been launched in new Terminal windows."
echo "You can close this initial terminal window."