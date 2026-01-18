#!/bin/sh

# FreeCAD MCP Server Start Script
# Activates virtual environment and starts the MCP server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Trap Ctrl+C for graceful shutdown
trap 'echo -e "\n\nShutting down FreeCAD MCP server..."; exit 0' INT TERM

echo "Starting FreeCAD MCP Server..."
echo "================================"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "✗ Virtual environment not found. Run: uv venv .venv --python 3.12"
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import mcp" 2>/dev/null; then
    echo "✗ Dependencies not installed. Run: uv pip install mcp-server httpx"
    exit 1
fi

echo "✓ Dependencies verified"
echo ""
echo "MCP Server is running. Press Ctrl+C to stop."
echo "================================"
echo ""

# Run the MCP server
python src/freecad_mcp_client.py "$@"
