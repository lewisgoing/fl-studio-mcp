# main.py
import logging
import atexit
import sys
import os
from typing import Dict, Any, List # For type hinting

# Ensure the project root is potentially in the path for imports
# If running as `python main.py` from the project root, this might not be needed
# If running as a module, imports should work if structure is correct
project_root = os.path.dirname(os.path.abspath(__file__))
# sys.path.insert(0, project_root) # Add project root to path if needed

try:
    from fastmcp import FastMCP
    # Import your refactored server components
    from server.midi_bridge import MidiBridge
    from server.feedback_handler import FeedbackHandler
    from server.command_map import CommandMapper
    # Import command constants if needed for validation
    # from shared.protocols import Command
except ImportError as e:
    print(f"ERROR: Failed to import necessary modules: {e}", file=sys.stderr)
    print("Please ensure you have installed requirements (fastmcp, mido) and the project structure is correct.", file=sys.stderr)
    sys.exit(1)


# --- Logging Setup ---
# (Consider moving to a shared utility module)
log_level = logging.INFO # Change to logging.DEBUG for more verbose output
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=log_level, format=log_format)
# Optionally configure file logging
# file_handler = logging.FileHandler("flstudio_mcp_server.log")
# file_handler.setFormatter(logging.Formatter(log_format))
# logging.getLogger().addHandler(file_handler) # Add handler to root logger

logger = logging.getLogger('flstudio-mcp.main')


# --- Configuration ---
# Match names used in FL Studio MIDI settings and macOS Audio MIDI Setup
OUTPUT_PORT_NAME_CONTAINS = 'IAC Driver MCP Bridge' # Server -> FL Studio device script
INPUT_PORT_NAME_CONTAINS = 'IAC Driver Bus 1'      # FL Studio device script -> Server
FEEDBACK_TIMEOUT = 7.0 # Default seconds to wait for command feedback (increase if needed)

# --- Initialize Core Components ---
logger.info("Initializing FL Studio MCP Server components...")

# Feedback handler needs to be created first
try:
    feedback_handler = FeedbackHandler(timeout=FEEDBACK_TIMEOUT)
    logger.info("FeedbackHandler initialized.")
except Exception as e:
     logger.exception("Fatal Error: Failed to initialize FeedbackHandler.")
     sys.exit(1)


# MIDI bridge needs the feedback handler's callback
try:
    midi_bridge = MidiBridge(
        output_port_name_contains=OUTPUT_PORT_NAME_CONTAINS,
        input_port_name_contains=INPUT_PORT_NAME_CONTAINS,
        sysex_callback=feedback_handler.handle_sysex_message # Pass the method reference
    )
    logger.info("MidiBridge initialized.")
except Exception as e:
     logger.exception("Fatal Error: Failed to initialize MidiBridge.")
     sys.exit(1)

# Command mapper uses the bridge and feedback handler
try:
    command_mapper = CommandMapper(midi_bridge, feedback_handler)
    logger.info("CommandMapper initialized.")
except Exception as e:
     logger.exception("Fatal Error: Failed to initialize CommandMapper.")
     sys.exit(1)


# Initialize MCP server (using FastMCP)
try:
    mcp = FastMCP("flstudio-mcp-refactored")
    logger.info("FastMCP server instance created.")
except Exception as e:
     logger.exception("Fatal Error: Failed to initialize FastMCP.")
     sys.exit(1)

# --- MCP Tool Definitions ---
# These functions are exposed via MCP and delegate to the CommandMapper.
# Add descriptions for better MCP integration/discovery.

@mcp.tool()
def get_channel_count() -> Dict[str, Any]:
    """Gets the number of channels currently visible in the FL Studio Channel Rack group."""
    return command_mapper.get_channel_count()

@mcp.tool()
def get_channel_names() -> Dict[str, Any]:
    """Gets the names of all channels in the current FL Studio Channel Rack group."""
    return command_mapper.get_channel_names()

@mcp.tool()
def get_channel_name(index: int) -> Dict[str, Any]:
     """Gets the name of a specific channel by its group index (0-based)."""
     if not isinstance(index, int) or index < 0:
         return {"status": "error", "message": "Channel index must be a non-negative integer."}
     return command_mapper.get_channel_name(index)

@mcp.tool()
def is_channel_selected(index: int) -> Dict[str, Any]:
    """Checks if a specific channel is selected by its group index (0-based)."""
    if not isinstance(index, int) or index < 0:
        return {"status": "error", "message": "Channel index must be a non-negative integer."}
    return command_mapper.is_channel_selected(index)

@mcp.tool()
def set_channel_color(index: int, color: int) -> Dict[str, Any]:
     """Sets the color (0xBBGGRR format integer) of a specific channel by group index (0-based)."""
     if not isinstance(index, int) or index < 0:
         return {"status": "error", "message": "Channel index must be a non-negative integer."}
     if not isinstance(color, int) or not (0 <= color <= 0xFFFFFF):
         return {"status": "error", "message": "Color must be an integer between 0x000000 and 0xFFFFFF."}
     return command_mapper.set_channel_color(index, color)

@mcp.tool()
def select_channel(index: int, mode: str = "toggle") -> Dict[str, Any]:
     """Selects, deselects, or toggles a channel by group index (0-based). Mode can be 'select', 'deselect', or 'toggle'."""
     mode_map = {"toggle": -1, "deselect": 0, "select": 1}
     value = mode_map.get(mode.lower())
     if value is None:
         return {"status": "error", "message": "Invalid mode. Use 'select', 'deselect', or 'toggle'."}
     if not isinstance(index, int) or index < 0:
         return {"status": "error", "message": "Channel index must be a non-negative integer."}
     return command_mapper.select_channel(index, value)

@mcp.tool()
def set_channel_volume(index: int, volume: float) -> Dict[str, Any]:
    """Sets the volume of a specific channel (0.0 to 1.0) by group index (0-based)."""
    if not isinstance(index, int) or index < 0:
        return {"status": "error", "message": "Channel index must be a non-negative integer."}
    try:
        volume_f = float(volume)
        if not (0.0 <= volume_f <= 1.0):
            raise ValueError("Volume out of range")
    except (ValueError, TypeError):
        return {"status": "error", "message": "Volume must be a number between 0.0 and 1.0."}
    return command_mapper.set_channel_volume(index, volume_f)

# --- Add MCP tools for Pan, Mute, Solo get/set ---

@mcp.tool()
def randomize_channel_colors(selected_only: bool = False) -> Dict[str, Any]:
     """Randomizes colors for all channels, or only the selected ones."""
     if not isinstance(selected_only, bool):
          return {"status": "error", "message": "selected_only parameter must be true or false."}
     return command_mapper.randomize_channel_colors(selected_only)

@mcp.tool()
def control_transport(action: str) -> Dict[str, Any]:
    """Controls FL Studio's transport. Actions: 'play', 'stop', 'record', 'toggle_play'."""
    valid_actions = ["play", "stop", "record", "toggle_play"]
    action_lower = action.lower()
    if action_lower not in valid_actions:
        return {"status": "error", "message": f"Invalid transport action '{action}'. Use one of: {valid_actions}"}
    return command_mapper.control_transport(action_lower)

@mcp.tool()
def get_is_playing() -> Dict[str, Any]:
    """Checks if FL Studio transport is currently playing."""
    return command_mapper.get_is_playing()

@mcp.tool()
def set_tempo(bpm: float) -> Dict[str, Any]:
    """Sets the project tempo in Beats Per Minute (BPM)."""
    try:
        bpm_f = float(bpm)
        if not (20.0 <= bpm_f <= 999.0): # Reasonable tempo range
             raise ValueError("Tempo out of range")
    except (ValueError, TypeError):
         return {"status": "error", "message": "BPM must be a number between 20 and 999."}
    return command_mapper.set_tempo(bpm_f)

@mcp.tool()
def get_tempo() -> Dict[str, Any]:
    """Gets the current project tempo in Beats Per Minute (BPM)."""
    return command_mapper.get_tempo()

@mcp.tool()
def select_pattern(pattern_number: int) -> Dict[str, Any]:
     """Selects a specific pattern number (1-based index) in FL Studio."""
     if not isinstance(pattern_number, int) or pattern_number < 1:
          return {"status": "error", "message": "Pattern number must be a positive integer (1-based)."}
     # Add upper limit check if possible (e.g., 999)
     return command_mapper.select_pattern(pattern_number)

@mcp.tool()
def get_current_pattern() -> Dict[str, Any]:
     """Gets the currently selected pattern number (1-based index) in FL Studio."""
     return command_mapper.get_current_pattern()

@mcp.tool()
def get_mixer_track_count() -> Dict[str, Any]:
    """Gets the total number of mixer tracks in the project."""
    return command_mapper.get_mixer_track_count()

@mcp.tool()
def get_mixer_level(track_index: int) -> Dict[str, Any]:
     """Gets the volume level (0.0 to 1.0) of a specific mixer track (0=Master, 1-125)."""
     if not isinstance(track_index, int) or track_index < 0: # Add upper bound check later if needed
         return {"status": "error", "message": "Mixer track index must be a non-negative integer."}
     return command_mapper.get_mixer_level(track_index)

@mcp.tool()
def set_mixer_level(track_index: int, level: float) -> Dict[str, Any]:
     """Sets the volume level (0.0 to 1.0) of a specific mixer track (0=Master, 1-125)."""
     if not isinstance(track_index, int) or track_index < 0:
         return {"status": "error", "message": "Mixer track index must be a non-negative integer."}
     try:
        level_f = float(level)
        if not (0.0 <= level_f <= 1.0): # FL mixer might go slightly above 1.0, adjust if needed
            raise ValueError("Level out of range")
     except (ValueError, TypeError):
        return {"status": "error", "message": "Level must be a number between 0.0 and 1.0."}
     return command_mapper.set_mixer_level(track_index, level_f)

@mcp.tool()
def add_audio_effect(track_index: int, effect_name: str) -> Dict[str, Any]:
    """Adds an audio effect (by name) to the first available slot on a mixer track."""
    if not isinstance(track_index, int) or track_index < 0:
        return {"status": "error", "message": "Mixer track index must be a non-negative integer."}
    if not isinstance(effect_name, str) or not effect_name:
        return {"status": "error", "message": "Effect name must be a non-empty string."}
    return command_mapper.add_audio_effect(track_index, effect_name)

# === Add MCP tools for all other commands defined in CommandMapper ===


# --- Main Execution Function ---
def run_server():
    """Initializes components and starts the MCP server loop."""
    logger.info("--- Starting FL Studio MCP Server (Refactored v2) ---")

    # Check if essential components initialized correctly
    if not midi_bridge or not feedback_handler or not command_mapper or not mcp:
         logger.critical("Core components failed to initialize. Server cannot start.")
         return

    # Verify MIDI ports needed for operation
    if not midi_bridge.output_port_name:
         logger.critical(f"Output MIDI port '{OUTPUT_PORT_NAME_CONTAINS}' not found. Cannot send commands.")
         # Exit or allow running in a degraded state? Exit is safer.
         return
    if not midi_bridge.input_port_name:
         logger.warning(f"Input MIDI port '{INPUT_PORT_NAME_CONTAINS}' not found. Feedback from FL Studio is disabled.")
         # Allow running without feedback if desired.

    # Start the MIDI listener thread
    midi_bridge.start_listener()

    # Start the MCP server (this is the main blocking loop)
    try:
        logger.info(f"MCP server starting. Listening for requests...")
        logger.info(f"Outputting MIDI to: {midi_bridge.output_port_name or 'None'}")
        logger.info(f"Inputting MIDI from: {midi_bridge.input_port_name or 'None'}")
        mcp.run() # Blocks here until MCP server stops
        logger.info("MCP server has stopped.")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.exception("An unexpected error occurred in the main MCP server loop.")
    finally:
        logger.info("Initiating server shutdown sequence...")
        # Cleanup (closing ports, stopping threads) is handled by atexit handler
        # Explicitly calling cleanup here might be redundant but ensures it happens before exit
        cleanup()
        logger.info("--- FL Studio MCP Server Finished ---")

# --- Cleanup Function ---
@atexit.register
def cleanup():
    """Registered function to ensure resources are released on exit."""
    logger.info("Running atexit cleanup...")
    if 'midi_bridge' in globals() and midi_bridge:
        midi_bridge.close_ports()
    logger.info("atexit cleanup complete.")


# --- Script Entry Point ---
if __name__ == "__main__":
    run_server()