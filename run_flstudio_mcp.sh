#!/bin/zsh

# Get the directory where this script is located
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" &> /dev/null && pwd)

# Change to the script's directory (which should be the project root)
cd "$SCRIPT_DIR"

# Activate the environment and run using the local UV install
source .venv/bin/activate
# python -m flstudio_mcp_iac.server "$@"

# Alternatively, use UV directly
.venv/bin/uv run flstudio-mcp-iac "$@"