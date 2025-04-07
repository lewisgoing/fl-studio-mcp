# FL Studio MCP - Model Context Protocol Integration

Connects FL Studio to AI models like Claude via the Model Context Protocol (MCP), allowing AI interaction with your FL Studio session.

**Note:** This integration relies on FL Studio's Python MIDI Scripting API, which has known limitations compared to other DAWs like Ableton Live, especially regarding detailed clip/note manipulation and automation.

## Features

-   Two-way communication between an AI assistant and FL Studio.
-   Basic session control: Play/Stop, Set Tempo.
-   Channel Rack manipulation: Create channels, rename channels.
-   Pattern control: Create/Select patterns, rename patterns.
-   Instrument loading (basic).

## Components

1.  **FL Studio MIDI Script (`device_FLStudioMCP.py`):** Runs inside FL Studio. It starts a local socket server that listens for commands from the MCP Server. Place this file correctly for FL Studio to recognize it.
2.  **MCP Server (`fl_mcp_server` package):** A Python application using `mcp-fastapi`. It exposes tools to the AI and communicates with the FL Studio Script via sockets.

## Installation

### Prerequisites

-   FL Studio 20.7 or newer (with Python scripting).
-   Python 3.9 or newer.
-   `pip` (Python package installer).
-   `uvx` (from `uv` recommended for running the MCP server via Claude Desktop). Install via `pip install uv`.

### 1. Install the FL Studio Script

1.  Locate your FL Studio User data folder:
    * **Windows:** `Documents\Image-Line\FL Studio\Settings\Hardware\`
    * **macOS:** `~/Documents/Image-Line/FL Studio/Settings/Hardware/`
2.  Create a new subfolder inside `Hardware`, for example, named `FLStudioMCP`.
3.  Copy the `device_FLStudioMCP.py` file from this repository into that new subfolder (`...\Hardware\FLStudioMCP\device_FLStudioMCP.py`).
4.  Restart FL Studio.
5.  Go to `OPTIONS > MIDI settings`.
6.  In the `Input` list, find the `Controller type` dropdown menu. Select **`FL Studio MCP (User)`**.
7.  Ensure **no** specific MIDI Input or Output port is assigned to this script unless you have a specific reason. The script communicates via network sockets, not direct MIDI ports.
8.  Make sure the script is **enabled**.

### 2. Install and Prepare the MCP Server

1.  Clone this repository:
    ```bash
    git clone [https://github.com/lewisgoing/fl-studio-mcp.git](https://www.google.com/search?q=https://github.com/lewisgoing/fl-studio-mcp.git) # Or your repo URL
    cd fl-studio-mcp
    ```
2.  Navigate to the repository directory in your terminal.
3.  **Recommended:** Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate # macOS/Linux
    # .\ .venv\Scripts\activate # Windows
    ```
4.  Install the MCP server package and its dependencies in editable mode:
    ```bash
    pip install -e .
    ```
    This installs the `fl_mcp_server` package and the `fl-mcp-server` command (if defined in `pyproject.toml`).

### 3. Configure Claude Desktop (or other MCP Client)

1.  Edit your MCP client's configuration (e.g., `claude_desktop_config.json`).
2.  Add an entry for the FL Studio MCP server. **Crucially**, ensure the `command` points to `uvx` within the **correct Python environment** where you installed `fl_mcp_server`.

    **Option A (Using Console Script Entry Point):** If `pip install -e .` worked and created the `fl-mcp-server` command (defined in `pyproject.toml`). *Replace `/path/to/your/.venv/bin/uvx` with the actual path if not using a venv or if installed globally.*

    ```json
    {
        "mcpServers": {
            "FLStudioMCP": {
                "command": "/path/to/your/.venv/bin/uvx", // Use uvx from the venv where fl_mcp_server was installed
                "args": [
                    "fl-mcp-server" // Command defined in pyproject.toml
                ]
                // Add "options": {"cwd": "/path/to/fl-studio-mcp"} if needed
            }
            // Add other servers like AbletonMCP if you have them
        }
    }
    ```

    **Option B (Running as a Module):** This is often more reliable if entry points cause issues.

    ```json
    {
        "mcpServers": {
            "FLStudioMCP": {
                "command": "/path/to/your/.venv/bin/uvx", // Use uvx from the venv
                "args": [
                    "python",               // Tell uvx to run python
                    "-m",                   // Tell python to run a module
                    "fl_mcp_server.server" // The module path to run (__main__ in server.py)
                ],
                // Add "options": {"cwd": "/path/to/fl-studio-mcp"} if needed,
                // though usually not required when running installed modules.
            }
        }
    }
    ```

    *Make sure the path to `uvx` is correct for your system and virtual environment.*

## Usage

1.  Start FL Studio. Ensure the `FL Studio MCP (User)` script is enabled in MIDI Settings. You should see log messages from the script in `VIEW > Script output`.
2.  Start your MCP client (e.g., Claude Desktop) with the updated configuration.
3.  Check the MCP client logs for messages from `FLStudioMCPServer`. It should indicate connection attempts to the script running in FL Studio.
4.  If the connection is successful, you should be able to use the defined tools via your AI assistant (e.g., "Ask FLStudioMCP to get session info").

## Troubleshooting

-   **"Connection refused" errors:**
    * Is FL Studio running?
    * Is the `FL Studio MCP (User)` script correctly installed in `...Hardware/FLStudioMCP/device_FLStudioMCP.py`?
    * Is the script enabled in FL Studio's MIDI Settings?
    * Check the FL Studio Script output (`VIEW > Script output`) for errors from `device_FLStudioMCP.py` (e.g., socket binding errors).
    * Is another application using port 9877?
-   **MCP Server fails to start (Check Claude logs):**
    * Did `pip install -e .` complete successfully in the correct environment?
    * Are you using the correct path to `uvx` in your Claude config?
    * Are there Python errors reported by `fl_mcp_server.server`? Check dependencies.
-   **Script not listed in FL Studio:**
    * Is the filename exactly `device_FLStudioMCP.py`?
    * Is it inside a subfolder within the `Hardware` directory?
    * Does the first line of the script contain `# name=FL Studio MCP (User)`?
    * Did you restart FL Studio after placing the file?
-   **Tools return errors:** Check the logs from both the FL Studio script (`VIEW > Script output`) and the MCP Server (Claude logs) for specific error messages from the FL Studio API.

## Disclaimer

This is a third-party integration. Use at your own risk. Not affiliated with Image-Line.