#!/bin/bash

# ==============================================================================
#  One-Click Start Script (macOS) - Single Virtual Environment Version
# ==============================================================================
# This script opens two new Terminal windows to run the server (backend) and
# the client (frontend).
# ==============================================================================

echo "🚀 Starting FastAPI Server and PyQt6 Client..."

# Get the absolute path of the directory where the script is located
BASE_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

# --- Define Commands ---

# SERVER_CMD
SERVER_CMD="source '$BASE_DIR/.venv/bin/activate' && \
             cd '$BASE_DIR/server' && \
             echo '--- 🐍 Starting Backend Server ---' && \
             uvicorn main:app --reload"

# CLIENT_CMD
CLIENT_CMD="source '$BASE_DIR/.venv/bin/activate' && \
              cd '$BASE_DIR' && \
              echo '--- 🖼️ Launching Frontend Client from project root ---' && \
              python -m client.main"


# --- Execute in New Terminal Windows using AppleScript ---

# Open a new terminal window for the server
osascript <<EOD
tell application "Terminal"
    do script "$SERVER_CMD"
end tell
EOD

# Give it a moment to launch
sleep 2

# Open another new terminal window for the client
osascript <<EOD
tell application "Terminal"
    do script "$CLIENT_CMD"
end tell
EOD

echo "✅ Both services have been launched in new Terminal windows."
echo "You can close this initial terminal window."