#!/bin/zsh
# Wrapper script to run the FL Studio MCP server

# Get the directory where this script is located
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" &> /dev/null && pwd)

# Change to the script's directory (which should be the project root)
cd "$SCRIPT_DIR"

# Execute the uv run command, passing along any arguments
/Users/lewisgoing/miniconda3/bin/uv run flstudio-mcp-iac "$@" 