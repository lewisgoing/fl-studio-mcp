#!/bin/zsh
# Get the directory where this script is located
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" &> /dev/null && pwd)
# Change to the script's directory (which should be the project root)
cd "$SCRIPT_DIR"
# Activate the environment and run using the local UV install or python
source .venv/bin/activate # Ensure environment is active
# Use uv run python main.py OR just python main.py if venv is active
.venv/bin/uv run python main.py "$@"
# OR simply:
# python main.py "$@"