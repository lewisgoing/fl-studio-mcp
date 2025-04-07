# fl_mcp_server/server.py
try:
    from mcp.server.fastmcp import FastMCP, Context
except ImportError:
     print("ERROR: fastapi-mcp not found. Please install it: pip install fastapi-mcp>=1.3.0", file=sys.stderr)
     sys.exit(1)

import socket
import json
import logging
import sys
import os # Added for potential path use
from dataclasses import dataclass, field
from contextlib import asynccontextmanager, closing # Added closing
from typing import AsyncIterator, Dict, Any, List, Union, Optional # Added Optional
import threading # Added for locks

# --- Logging Setup ---
# Configure logging BEFORE defining functions that use it
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stderr)])
logger = logging.getLogger("FLStudioMCPServer")

logger.info(f"FL Studio MCP Server starting up... Log level: {log_level}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")



# --- FL Studio Connection Class ---
@dataclass
class FLStudioConnection:
    host: str = "localhost"
    port: int = 9877 # Default port defined in device_FLStudioMCP.py
    sock: Optional[socket.socket] = None
    lock: threading.Lock = field(default_factory=threading.Lock) # Ensure thread safety

    def connect(self) -> bool:
        """Connect to the FL Studio Remote Script socket server"""
        with self.lock: # Acquire lock for connection attempt
            if self.sock:
                # Double check if still connected
                try:
                    self.sock.getpeername()
                    return True # Already connected
                except socket.error:
                    logger.warning("Existing socket found but disconnected. Reconnecting.")
                    self.sock.close()
                    self.sock = None

            logger.info(f"Attempting to connect to FL Studio script at {self.host}:{self.port}")
            try:
                # Use create_connection for potentially better IPv6 handling and options
                self.sock = socket.create_connection((self.host, self.port), timeout=5.0)
                self.sock.settimeout(15.0) # Set default timeout for operations
                logger.info(f"Successfully connected to FL Studio script.")
                return True
            except socket.timeout:
                logger.error(f"Connection timed out connecting to {self.host}:{self.port}")
                self.sock = None
                return False
            except socket.error as e:
                logger.error(f"Failed to connect to FL Studio script: {e}")
                self.sock = None
                return False
            except Exception as e:
                 logger.error(f"Unexpected error during connection: {e}", exc_info=True)
                 self.sock = None
                 return False

    def disconnect(self):
        """Disconnect from the FL Studio Remote Script"""
        with self.lock: # Acquire lock
            if self.sock:
                logger.info("Disconnecting from FL Studio script.")
                try:
                    self.sock.shutdown(socket.SHUT_RDWR) # Graceful shutdown
                    self.sock.close()
                except socket.error as e:
                    # Ignore errors on close/shutdown, socket might already be dead
                    logger.debug(f"Socket error during disconnect (ignorable): {e}")
                except Exception as e:
                    logger.error(f"Unexpected error during disconnect: {e}", exc_info=True)
                finally:
                    self.sock = None
            else:
                logger.debug("Disconnect called but not connected.")


    def send_command(self, command_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a command to FL Studio and return the response"""
        with self.lock: # Acquire lock for the entire send/receive operation
            if not self.sock and not self.connect():
                # Connect failed, raise error after releasing lock
                raise ConnectionError("Not connected to FL Studio script and connection failed.")

            command = {
                "type": command_type,
                "params": params or {}
            }
            command_json = json.dumps(command).encode('utf-8')

            try:
                logger.info(f"Sending command: {command_type}, params: {params}")
                self.sock.sendall(command_json)
                logger.debug(f"Command sent ({len(command_json)} bytes), waiting for response...")

                # Receive the response (handle potential fragmentation)
                buffer = b''
                while True:
                    try:
                        # Use a reasonable timeout for recv
                        self.sock.settimeout(20.0) # Slightly longer timeout for potentially slow FL ops
                        chunk = self.sock.recv(8192)
                        if not chunk:
                            logger.error("Connection closed by FL Studio script while waiting for response.")
                            self.disconnect() # Clean up our side
                            raise ConnectionAbortedError("Connection closed unexpectedly by FL Studio script.")
                        buffer += chunk

                        # Attempt to decode the buffer
                        try:
                            response = json.loads(buffer.decode('utf-8'))
                            # If decode succeeds, we have the full message
                            logger.debug(f"Received full response ({len(buffer)} bytes).")
                            break
                        except json.JSONDecodeError:
                            # Message is not complete yet, continue receiving
                            logger.debug(f"Received partial response ({len(buffer)} bytes), waiting for more...")
                            continue

                    except socket.timeout:
                        logger.error("Socket timeout while waiting for response from FL Studio script.")
                        self.disconnect() # Assume connection is dead
                        raise TimeoutError("Timeout waiting for response from FL Studio script.")
                    except socket.error as e:
                         logger.error(f"Socket error during receive: {e}")
                         self.disconnect()
                         raise ConnectionAbortedError(f"Socket error receiving response: {e}")

                logger.info(f"Response received, status: {response.get('status', 'unknown')}")

                if response.get("status") == "error":
                    error_message = response.get("message", "Unknown error from FL Studio script")
                    logger.error(f"Received error response from FL Studio script: {error_message}")
                    # Don't necessarily raise an Exception here, let the tool return the error message
                    # raise Exception(error_message)
                    # Return the error structure so Claude knows it failed
                    return {"status": "error", "message": error_message}


                return response # Return the full response dictionary

            except ConnectionAbortedError as e:
                 # Connection already handled by disconnect()
                 raise e # Re-raise specific connection error
            except TimeoutError as e:
                 # Connection already handled by disconnect()
                 raise e # Re-raise timeout error
            except socket.error as e:
                 logger.error(f"Socket communication error: {e}")
                 self.disconnect() # Clean up connection
                 raise ConnectionError(f"Socket communication error with FL Studio script: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during command send/receive: {e}", exc_info=True)
                 self.disconnect() # Clean up connection
                 raise Exception(f"Unexpected communication error: {e}")

# --- Server Lifespan and Connection Management ---
# Global connection instance (managed within lifespan)
_fl_studio_connection: Optional[FLStudioConnection] = None

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle, including FL Studio connection."""
    global _fl_studio_connection
    logger.info("MCP Server lifespan starting...")
    # Create and attempt connection on startup
    _fl_studio_connection = FLStudioConnection()
    try:
        if _fl_studio_connection.connect():
            logger.info("Initial connection to FL Studio script successful.")
            # Optional: Send a test command like get_session_info on startup?
            # try:
            #    info = _fl_studio_connection.send_command("get_session_info")
            #    logger.info(f"FL Studio Session Info on startup: {info.get('tempo', 'N/A')} BPM")
            # except Exception as e:
            #    logger.warning(f"Test command failed on startup: {e}")
        else:
            logger.warning("Initial connection to FL Studio script FAILED. Is FL Studio running with the script?")
    except Exception as e:
        logger.error(f"Error during initial connection attempt: {e}", exc_info=True)
        # Ensure connection object is cleaned up if connect fails partially
        if _fl_studio_connection:
             _fl_studio_connection.disconnect()
             _fl_studio_connection = None

    try:
        yield {} # Server runs here
    finally:
        logger.info("MCP Server lifespan ending...")
        if _fl_studio_connection:
            logger.info("Disconnecting from FL Studio script during shutdown.")
            _fl_studio_connection.disconnect()
            _fl_studio_connection = None
        logger.info("FL Studio MCP server shut down complete.")

def get_fl_studio_connection_instance() -> FLStudioConnection:
    """Gets the managed FL Studio connection instance. Raises if not connected."""
    if _fl_studio_connection is None:
        # This shouldn't happen if lifespan management is correct, but handle defensively
        logger.error("Accessing FL Studio connection outside of managed lifespan or after failure.")
        raise ConnectionError("FL Studio connection is not available (server starting/stopping or connection failed).")

    # Optional: Add a check here to ensure connection is still live before returning?
    # Could do a quick connect() check, but might add latency.
    # Relying on send_command to handle reconnections might be sufficient.

    return _fl_studio_connection


# --- MCP Server Definition ---
mcp = FastMCP(
    # Use the package name for the tool name for clarity
    tool_name="FLStudioMCP",
    description="Provides tools to interact with Image-Line FL Studio.",
    lifespan=server_lifespan # Use the lifespan manager
)

@mcp.method("initialize")
def initialize(ctx: Context, params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Received initialize request from Claude")
    return {
        "jsonrpc": "2.0",
        "id": params.get("id"),
        "result": {
            "capabilities": {},
            "serverInfo": {
                "name": "FLStudioMCP",
                "version": "0.1.0"
            }
        }
    }

# --- Tool Definitions ---
# Decorate functions to expose them as tools via MCP

# Helper to handle FL Studio errors consistently
def handle_fl_studio_call(command_type: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Calls FL Studio, handles errors, and formats the response for Claude."""
    try:
        fl_studio = get_fl_studio_connection_instance()
        response = fl_studio.send_command(command_type, params)

        if response.get("status") == "error":
            return f"Error from FL Studio: {response.get('message', 'Unknown error')}"
        else:
            # Success, return a formatted string or JSON dump
            result = response.get('result', {})
            # Simple success message for actions, JSON for info retrieval
            if command_type.startswith("get_"):
                 return json.dumps(result, indent=2)
            elif result:
                 # Try to provide a meaningful success message from the result
                 return f"Success: {json.dumps(result)}"
            else:
                 return f"Command '{command_type}' executed successfully."

    except ConnectionError as e:
        logger.error(f"Connection error during '{command_type}': {e}")
        return f"Error: Could not connect to FL Studio. Please ensure FL Studio is running with the 'FL Studio MCP (User)' script enabled in MIDI settings. Details: {e}"
    except TimeoutError as e:
         logger.error(f"Timeout error during '{command_type}': {e}")
         return f"Error: Timeout communicating with FL Studio. The operation may not have completed. Details: {e}"
    except Exception as e:
        logger.error(f"Unexpected error executing '{command_type}': {e}", exc_info=True)
        return f"Error: An unexpected error occurred. Details: {e}"


@mcp.tool()
def get_session_info(ctx: Context) -> str:
    """Get detailed information about the current FL Studio session, including tempo, time signature, track count, and master track details."""
    return handle_fl_studio_call("get_session_info")

@mcp.tool()
def get_track_info(ctx: Context, track_index: int) -> str:
    """
    Get detailed information about a specific track (Channel) in FL Studio.

    Args:
        track_index: The zero-based index of the track (Channel) in the Channel Rack.
    """
    if not isinstance(track_index, int) or track_index < 0:
         return "Error: track_index must be a non-negative integer."
    return handle_fl_studio_call("get_track_info", {"track_index": track_index})

@mcp.tool()
def create_midi_track(ctx: Context) -> str:
    """
    Create a new MIDI track (Channel with a Sampler) in the FL Studio Channel Rack.
    Returns the index and name of the newly created channel.
    """
    # 'index' param removed as FL Studio appends channels
    return handle_fl_studio_call("create_midi_track")

@mcp.tool()
def set_track_name(ctx: Context, track_index: int, name: str) -> str:
    """
    Set the name of a specific track (Channel) in FL Studio.

    Args:
        track_index: The zero-based index of the track (Channel) to rename.
        name: The new desired name for the track.
    """
    if not isinstance(track_index, int) or track_index < 0:
         return "Error: track_index must be a non-negative integer."
    if not name or not isinstance(name, str):
        return "Error: name must be a non-empty string."
    return handle_fl_studio_call("set_track_name", {"track_index": track_index, "name": name})

@mcp.tool()
def create_clip(ctx: Context, pattern_index: int, length_beats: float = 4.0) -> str:
    """
    Create or select a pattern in FL Studio. If pattern_index exists, it selects it. If it's beyond the current count, it creates new patterns up to that index. If -1, creates a new pattern.

    Args:
        pattern_index: The zero-based index of the pattern. Use -1 to create a new pattern at the end.
        length_beats: The desired length in beats (Note: FL Studio API for setting length might be limited). Default: 4.0.
    """
    if not isinstance(pattern_index, int):
         return "Error: pattern_index must be an integer."
    if not isinstance(length_beats, (int, float)) or length_beats <= 0:
         return "Error: length_beats must be a positive number."
    # MCP uses 'clip_index', map it to 'pattern_index' for FL Studio
    return handle_fl_studio_call("create_clip", {"clip_index": pattern_index, "length": length_beats})

# @mcp.tool()
# def add_notes_to_clip(...) -> str:
#    """(Currently Non-Functional) Add MIDI notes to a pattern."""
#    # This remains difficult due to FL API limits. Keep commented out or clearly mark as experimental.
#    return "Error: Adding notes via script is currently not supported due to FL Studio API limitations."

@mcp.tool()
def set_clip_name(ctx: Context, pattern_index: int, name: str) -> str:
    """
    Set the name of a specific pattern in FL Studio.

    Args:
        pattern_index: The zero-based index of the pattern to rename.
        name: The new desired name for the pattern.
    """
    if not isinstance(pattern_index, int) or pattern_index < 0:
         return "Error: pattern_index must be a non-negative integer."
    if not name or not isinstance(name, str):
        return "Error: name must be a non-empty string."
    # MCP uses 'clip_index', map it
    return handle_fl_studio_call("set_clip_name", {"pattern_index": pattern_index, "name": name})


@mcp.tool()
def set_tempo(ctx: Context, tempo_bpm: float) -> str:
    """
    Set the master tempo of the FL Studio session.

    Args:
        tempo_bpm: The new tempo in Beats Per Minute (BPM). Must be positive.
    """
    if not isinstance(tempo_bpm, (int, float)) or tempo_bpm <= 0:
        return "Error: tempo_bpm must be a positive number."
    return handle_fl_studio_call("set_tempo", {"tempo": tempo_bpm})

@mcp.tool()
def fire_clip(ctx: Context, pattern_index: int) -> str:
    """
    Start playing a specific pattern in FL Studio. Puts FL Studio in Pattern mode if necessary and starts playback.

    Args:
        pattern_index: The zero-based index of the pattern to play.
    """
    if not isinstance(pattern_index, int) or pattern_index < 0:
         return "Error: pattern_index must be a non-negative integer."
    # Map MCP 'clip_index' to FL 'pattern_index'
    # Track index isn't needed for this FL action
    return handle_fl_studio_call("fire_clip", {"pattern_index": pattern_index})

@mcp.tool()
def stop_clip(ctx: Context, pattern_index: Optional[int] = None) -> str:
    """
    Stop playback in FL Studio. (Note: FL Studio typically stops the entire transport, not individual patterns via basic API).

    Args:
        pattern_index: (Optional) The index of the pattern. Currently ignored by the FL script, stops global transport.
    """
    # Parameters are optional as we just stop the transport
    return handle_fl_studio_call("stop_clip") # track/pattern index ignored by handler

@mcp.tool()
def start_playback(ctx: Context) -> str:
    """Starts the main transport playback in FL Studio (Song or Pattern mode, whichever is active)."""
    return handle_fl_studio_call("start_playback")

@mcp.tool()
def stop_playback(ctx: Context) -> str:
    """Stops the main transport playback in FL Studio."""
    return handle_fl_studio_call("stop_playback")

@mcp.tool()
def load_instrument(ctx: Context, track_index: int, instrument_name: str) -> str:
    """
    Loads an instrument (Generator) onto a specific track (Channel) in FL Studio, replacing the existing one.

    Args:
        track_index: The zero-based index of the track (Channel) to load the instrument onto.
        instrument_name: The name of the FL Studio instrument/generator to load (e.g., "FLEX", "Sytrus", "Sampler"). Name must match FL browser name.
    """
    if not isinstance(track_index, int) or track_index < 0:
         return "Error: track_index must be a non-negative integer."
    if not instrument_name or not isinstance(instrument_name, str):
        return "Error: instrument_name must be a non-empty string."
    return handle_fl_studio_call("load_instrument_or_effect", {"track_index": track_index, "instrument_name": instrument_name})


# --- Main Execution ---
# Allow running the server directly using `python -m fl_mcp_server.server`
def main():
    """Main function to run the MCP server."""
    logger.info("Starting FL Studio MCP Server...")
    try:
        # FastMCP uses uvicorn internally, mcp.run() handles the server start
        mcp.run()
        logger.info("FL Studio MCP Server finished.")
    except Exception as e:
         logger.critical(f"Failed to run MCP server: {e}", exc_info=True)
         sys.exit(1)


if __name__ == "__main__":
    main()