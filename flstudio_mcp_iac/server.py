# Full server.py code - Ready for pushing
import mido
import time
import logging
import json
import threading
import queue
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
import atexit # For cleanup

# Setup logging
logging.basicConfig(
    level=logging.INFO, # Change to logging.DEBUG for more verbose logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flstudio-mcp')

# Initialize MCP server
mcp: FastMCP = FastMCP("flstudio-mcp")

# --- MIDI Port Handling ---
output_port: Optional[mido.ports.BaseOutput] = None
input_port: Optional[mido.ports.BaseInput] = None

# --- Port names based on user's latest configuration ---
OUTPUT_PORT_NAME_CONTAINS = 'IAC Driver MCP Bridge' # Server sends commands TO FL Studio via this
INPUT_PORT_NAME_CONTAINS = 'IAC Driver Bus 1'      # Server receives feedback FROM FL Studio via this
# --- End of port names ---


# --- Feedback Handling ---
feedback_queue = queue.Queue()
feedback_listener_thread = None
stop_listener_flag = threading.Event()
FEEDBACK_TIMEOUT = 5.0 # seconds to wait for feedback

def find_midi_port(port_names: List[str], contains_str: str) -> Optional[str]:
    """Finds the first port name containing a specific string."""
    logger.debug(f"Searching for port containing '{contains_str}' in {port_names}")
    # Prioritize exact match or specified substring
    for port in port_names:
        if contains_str in port:
            logger.debug(f"Found match: '{port}'")
            return port

    # Fallback to any IAC port if specific one not found
    # Avoid reusing the *other* designated port if possible
    other_port_str = OUTPUT_PORT_NAME_CONTAINS if contains_str == INPUT_PORT_NAME_CONTAINS else INPUT_PORT_NAME_CONTAINS
    logger.debug(f"Specific port '{contains_str}' not found. Falling back. Will avoid '{other_port_str}' if possible.")
    for port in port_names:
         # Check if 'IAC' is in the name AND it's not the *other* specified port
         # unless the input and output names are supposed to be the same
         if 'IAC' in port:
            if contains_str == other_port_str or other_port_str not in port:
                 logger.warning(f"Falling back to first available IAC port: '{port}' for target '{contains_str}'")
                 return port

    logger.error(f"Could not find any suitable port for '{contains_str}'")
    return None

try:
    # --- Output Port ---
    available_output_ports = mido.get_output_names()
    logger.info(f"Available MIDI output ports: {available_output_ports}")
    output_port_name = find_midi_port(available_output_ports, OUTPUT_PORT_NAME_CONTAINS)

    if output_port_name:
        output_port = mido.open_output(output_port_name)
        logger.info(f"Connected to MIDI output port: {output_port_name}")
    else:
        logger.error(f"Could not find suitable MIDI output port containing '{OUTPUT_PORT_NAME_CONTAINS}'. Please configure your MIDI ports.")

    # --- Input Port ---
    available_input_ports = mido.get_input_names()
    logger.info(f"Available MIDI input ports: {available_input_ports}")
    input_port_name = find_midi_port(available_input_ports, INPUT_PORT_NAME_CONTAINS)

    if input_port_name:
        # Store the name, but open the port later in the listener thread function
        logger.info(f"Found MIDI input port for feedback: {input_port_name}")
    else:
        logger.error(f"Could not find suitable MIDI input port containing '{INPUT_PORT_NAME_CONTAINS}'. Feedback will not be received. Please configure your MIDI ports.")

except Exception as e:
    logger.exception(f"Error initializing MIDI: {e}")

# --- MIDI Input Listener ---
def midi_input_callback(msg):
    """Callback function executed by mido for each incoming message."""
    global feedback_queue
    if msg.type == 'sysex':
        logger.debug(f"Received SysEx: {msg.hex()}")
        try:
            data = msg.data
            # Check for our specific header F0 00 01 ... F7
            # mido's data tuple does NOT include F0 and F7
            if len(data) > 2 and data[0] == 0x00 and data[1] == 0x01:
                # Extract JSON payload (bytes between header and end)
                payload_bytes = bytes(data[2:])
                payload_str = payload_bytes.decode('utf-8', errors='ignore')
                logger.debug(f"Decoded SysEx payload string: {payload_str}")

                # Parse JSON
                feedback_data = json.loads(payload_str)
                logger.info(f"Parsed feedback received: {feedback_data}")
                feedback_queue.put(feedback_data)
            else:
                logger.debug(f"Ignoring SysEx with unknown header: {msg.hex()}")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from SysEx: {payload_str}")
        except Exception as e:
            logger.exception(f"Error processing SysEx message: {e}")
    # Optionally log other message types for debugging
    # else:
    #     logger.debug(f"Received other MIDI message: {msg}")


def midi_listener_func(port_name):
    """Function to run in the listener thread."""
    global input_port, stop_listener_flag
    retries = 3
    wait_time = 2
    for attempt in range(retries):
        try:
            # Open the input port within the thread
            input_port = mido.open_input(port_name, callback=midi_input_callback)
            logger.info(f"MIDI input listener started on port: {port_name}")
            # Keep the thread alive while the main program runs, checking the stop flag
            while not stop_listener_flag.is_set():
                # The callback handles messages, we just need to keep the thread alive.
                # Mido might handle callbacks in a separate thread, but sleeping here
                # prevents this thread from busy-waiting unnecessarily.
                time.sleep(0.1)
            # If loop exits cleanly via flag
            logger.info("Stop flag set, listener thread exiting.")
            break # Exit retry loop
        except Exception as e:
            logger.error(f"MIDI input listener failed on attempt {attempt + 1}: {e}")
            if input_port and not input_port.closed:
                try: input_port.close()
                except: pass # Ignore errors during cleanup on failure
            input_port = None
            if attempt < retries - 1:
                logger.info(f"Retrying listener start in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("MIDI input listener failed after multiple retries.")
                break # Exit retry loop
    # Final cleanup check
    if input_port and not input_port.closed:
        try:
            logger.info("Closing MIDI input port in listener finally block.")
            input_port.close()
        except Exception as e:
            logger.error(f"Error closing input port during final cleanup: {e}")
    logger.info("MIDI input listener thread stopped.")


def start_midi_listener():
    """Starts the MIDI listener thread if an input port was found."""
    global feedback_listener_thread, input_port_name
    if input_port_name and (feedback_listener_thread is None or not feedback_listener_thread.is_alive()):
        stop_listener_flag.clear()
        feedback_listener_thread = threading.Thread(target=midi_listener_func, args=(input_port_name,), daemon=True)
        feedback_listener_thread.start()
        logger.info("MIDI feedback listener thread started.")
    elif not input_port_name:
         logger.warning("Cannot start MIDI listener: No suitable input port found/configured.")
    elif feedback_listener_thread and feedback_listener_thread.is_alive():
         logger.info("MIDI listener thread already running.")


def stop_midi_listener():
    """Signals the MIDI listener thread to stop and waits for it."""
    global feedback_listener_thread, stop_listener_flag, input_port
    if feedback_listener_thread and feedback_listener_thread.is_alive():
        logger.info("Stopping MIDI feedback listener thread...")
        stop_listener_flag.set()
        # No need to explicitly close input_port here, listener thread's finally block should handle it
        feedback_listener_thread.join(timeout=2.0) # Wait max 2 seconds
        if feedback_listener_thread.is_alive():
             logger.warning("Listener thread did not stop gracefully after timeout.")
        else:
             logger.info("Listener thread stopped.")
        feedback_listener_thread = None
    else:
        logger.info("Listener thread was not running or already stopped.")
    # Additional safety close if port object still exists and is open
    if input_port and not input_port.closed:
        logger.warning("Listener thread stopped, but input port object reference still open. Closing.")
        try:
            input_port.close()
        except Exception as e:
            logger.error(f"Error during safety close of input port: {e}")
        input_port = None


# Register cleanup functions
@atexit.register
def cleanup_ports():
    logger.info("Running atexit cleanup...")
    stop_midi_listener() # Ensure listener is stopped first
    if output_port and not output_port.closed:
        logger.info("Closing MIDI output port.")
        try:
            output_port.close()
        except Exception as e:
             logger.error(f"Error closing output port during cleanup: {e}")
    logger.info("Cleanup complete.")


# --- Command Sending ---
def send_command(command_type: int, params: Optional[Dict[str, Any]] = None, wait_for_feedback: bool = True, timeout: float = FEEDBACK_TIMEOUT) -> Dict[str, Any]:
    """
    Send a command to FL Studio via MIDI CC and optionally wait for SysEx feedback.
    """
    if output_port is None:
        logger.error("Cannot send command: No MIDI output port available")
        return {"status": "error", "message": "No MIDI output port available"}

    # Check listener status before proceeding if feedback is expected
    if wait_for_feedback:
        if feedback_listener_thread is None or not feedback_listener_thread.is_alive():
            logger.error("Cannot wait for feedback: MIDI listener thread is not running.")
            # Decide whether to send anyway or return error immediately
            # Sending anyway without listener = guaranteed timeout later
            return {"status": "error", "message": "Command not sent: feedback listener is not running."}
        if input_port is None or input_port.closed:
             # This check might be redundant if listener thread handles port opening robustly
            logger.error("Cannot wait for feedback: MIDI input port is not open.")
            return {"status": "error", "message": "Command not sent: input port is not open."}
        # Clear the feedback queue only if listener seems ready
        while not feedback_queue.empty():
            try:
                feedback_queue.get_nowait()
            except queue.Empty:
                break
        logger.debug("Cleared old feedback from queue.")

    try:
        # --- Send Command Sequence ---
        logger.debug(f"Sending Command Type: {command_type} with Params: {params}")
        # Command start
        output_port.send(mido.Message('control_change', control=120, value=command_type))
        logger.debug(f"Sent CC 120: {command_type}")
        time.sleep(0.01) # Small delay

        # Send parameters
        # Mapping from descriptive names to CC numbers (as handled in FL script)
        param_map = {
            "track": 121, "channel": 121, "index": 121, # For selecting channels/tracks
            "pattern": 122, "bpm": 122,             # For patterns, tempo value
            "value": 123, "level": 123,             # For general values, mixer levels
            "action": 124, "type": 124,             # For actions (play/stop), types (instrument/effect)
            "instrument": 125, "name": 125, "effect": 125 # For instrument/effect selection/name (reuse CC)
        }

        if params:
            logger.debug(f"Sending parameters: {params}")
            for key, value in params.items():
                param_cc = param_map.get(key.lower())
                if param_cc:
                    # Convert value to MIDI 0-127 range
                    midi_value = 0
                    if isinstance(value, bool):
                        midi_value = 127 if value else 0
                    elif isinstance(value, float):
                        # Scale float assumed to be 0.0-1.0 to 0-127
                        midi_value = int(max(0.0, min(1.0, value)) * 127)
                    elif isinstance(value, int):
                        # Clamp integer to 0-127
                        midi_value = max(0, min(127, value))
                    # Add handling for string names if needed (e.g., sending name parts via multiple CCs - complex)
                    elif isinstance(value, str):
                         logger.warning(f"Parameter '{key}' is a string ('{value}'). Cannot send directly via single CC. Ignoring.")
                         continue # Skip sending this param
                    else:
                        logger.warning(f"Cannot convert param type {type(value)} for key '{key}' to MIDI, sending 0.")
                        midi_value = 0

                    output_port.send(mido.Message('control_change', control=param_cc, value=midi_value))
                    logger.debug(f"Sent CC {param_cc}: {midi_value} (for key '{key}')")
                    time.sleep(0.01) # Small delay between parameters
                else:
                    logger.warning(f"Unknown parameter key: '{key}'. Cannot send.")
        else:
             logger.debug("No parameters to send.")

        # Command end
        output_port.send(mido.Message('control_change', control=126, value=127))
        logger.debug("Sent CC 126 (Command End)")
        # --- End Send Command Sequence ---


        # Wait for feedback if requested
        if wait_for_feedback:
            logger.debug(f"Waiting for feedback (timeout: {timeout}s)...")
            try:
                # Get feedback from the queue populated by the listener thread
                feedback = feedback_queue.get(block=True, timeout=timeout)
                logger.info(f"Successfully received feedback: {feedback}")
                # Check if feedback itself indicates an error from the script side
                if isinstance(feedback, dict) and feedback.get('status') == 'error':
                    logger.error(f"Received error status from FL Studio script: {feedback.get('message', 'No message')}")
                return feedback # Return the parsed JSON data directly
            except queue.Empty:
                logger.warning(f"Timeout waiting for feedback for command {command_type}.")
                return {"status": "error", "message": "Timeout waiting for feedback from FL Studio."}
            except Exception as e:
                 logger.exception(f"Exception while waiting for or processing feedback: {e}")
                 return {"status": "error", "message": f"Error processing feedback: {str(e)}"}
        else:
            # If not waiting for feedback, return basic success confirmation
            return {"status": "success", "message": "Command sent successfully (no feedback requested).", "command": command_type, "params": params}

    except mido.MidiError as e:
        logger.error(f"MIDI Error during send_command: {e}")
        # Potentially try to reset the port or handle specific errors
        return {"status": "error", "message": f"MIDI Error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error sending command or processing feedback: {e}")
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


# --- MCP Tool Implementations ---

@mcp.tool()
def get_midi_ports() -> Dict[str, Any]:
    """Get available MIDI input and output ports detected by Mido."""
    try:
        outs = mido.get_output_names() # type: ignore
        ins = mido.get_input_names() # type: ignore
        logger.info(f"Available MIDI outputs: {outs}")
        logger.info(f"Available MIDI inputs: {ins}")
        return {"status": "success", "outputs": outs, "inputs": ins}
    except Exception as e:
        logger.exception(f"Error getting MIDI ports: {e}")
        return {"status": "error", "message": f"Error getting MIDI ports: {str(e)}"}

@mcp.tool()
def play_note(note: int, velocity: int = 100, duration: float = 0.5) -> Dict[str, Any]:
    """
    Play a single MIDI note directly (bypasses command protocol).
    Sends Note On, waits, sends Note Off on the configured output port.
    """
    if output_port is None: return {"status": "error", "message": "No MIDI output port available"}
    if not 0 <= note <= 127: return {"status": "error", "message": "Note must be between 0 and 127"}
    if not 0 <= velocity <= 127: return {"status": "error", "message": "Velocity must be between 0 and 127"}
    if duration <= 0: return {"status": "error", "message": "Duration must be positive"}

    try:
        msg_on = mido.Message('note_on', note=note, velocity=velocity)
        msg_off = mido.Message('note_off', note=note, velocity=0)
        logger.debug(f"Sending direct MIDI: {msg_on}")
        output_port.send(msg_on)
        time.sleep(duration)
        logger.debug(f"Sending direct MIDI: {msg_off}")
        output_port.send(msg_off)
        logger.info(f"Played note {note} (vel={velocity}, dur={duration}s)")
        return {"status": "success", "note": note, "velocity": velocity, "duration": duration}
    except Exception as e:
        logger.exception(f"Error playing note directly: {e}")
        return {"status": "error", "message": f"Error playing note: {str(e)}"}

# --- Channel Info Tools (Using Command Protocol with Feedback) ---

@mcp.tool()
def get_channel_names() -> Dict[str, Any]:
    """Gets the names of all channels by requesting them from FL Studio via MIDI command 12."""
    logger.info("Requesting all channel names from FL Studio (Cmd 12)...")
    # Assumes command type 12 is handled in device_FLStudioMCPController.py
    # and sends back feedback like: {"status": "success", "names": ["Name1", "Name2", ...]}
    result = send_command(command_type=12, wait_for_feedback=True)
    return result

@mcp.tool()
def get_channel_name(index: int) -> Dict[str, Any]:
     """Gets the name of a specific channel by index via MIDI command 13."""
     if not 0 <= index <= 127: # Basic validation for MIDI param range
         return {"status": "error", "message": "Index must be between 0 and 127"}
     logger.info(f"Requesting channel name for index {index} from FL Studio (Cmd 13)...")
     # Assumes command type 13 is handled in device_FLStudioMCPController.py
     # Needs param 'index' (mapped to CC 121)
     # Expects feedback like: {"status": "success", "index": index, "name": "TheName"}
     result = send_command(command_type=13, params={"index": index}, wait_for_feedback=True)
     return result

# --- Transport and Pattern Tools ---

@mcp.tool()
def set_tempo(bpm: int) -> Dict[str, Any]:
    """Sets the project tempo via MIDI command 4."""
    if not 1 <= bpm <= 999: # Adjusted lower bound, FL might support lower tempos
        return {"status": "error", "message": "BPM must be between 1 and 999"}
    logger.info(f"Sending command to set tempo towards {bpm} BPM (Cmd 4)...")
    # Check device_FLStudioMCPController.py: Cmd 4 uses 'pattern' param for tempo CC value.
    # FL script needs to map this value back to BPM.
    # Simple clamping for param, FL script needs the real mapping logic.
    bpm_param_value = max(0, min(127, bpm))
    logger.debug(f"Mapping BPM {bpm} to parameter value {bpm_param_value}")

    result = send_command(command_type=4, params={"pattern": bpm_param_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send tempo command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Command to set tempo towards {bpm} sent."}


@mcp.tool()
def control_transport(action: str) -> Dict[str, Any]:
    """Controls transport (play, stop, record, toggle) via MIDI command 5."""
    action_map = {"play": 0, "stop": 1, "record": 2, "toggle": 3}
    action_value = action_map.get(action.lower())

    if action_value is None:
        return {"status": "error", "message": f"Invalid transport action: '{action}'. Use play, stop, record, or toggle."}

    logger.info(f"Sending transport control command: {action} (Cmd 5)...")
    # device_FLStudioMCPController.py: Cmd 5 uses 'action' param.
    result = send_command(command_type=5, params={"action": action_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send transport command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Transport command '{action}' sent."}


@mcp.tool()
def select_pattern(pattern_number: int) -> Dict[str, Any]:
    """Selects a pattern by number via MIDI command 6."""
    if not 1 <= pattern_number <= 999: # FL Patterns are 1-999
         return {"status": "error", "message": "Pattern number must be between 1 and 999"}
    logger.info(f"Sending command to select pattern {pattern_number} (Cmd 6)...")
    # device_FLStudioMCPController.py: Cmd 6 uses 'pattern' param. Assume clamped value.
    pattern_param_value = max(0, min(127, pattern_number))
    logger.debug(f"Mapping pattern {pattern_number} to parameter value {pattern_param_value}")

    result = send_command(command_type=6, params={"pattern": pattern_param_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send select pattern command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Command to select pattern {pattern_number} sent."}

# --- Mixer and Effects Tools ---

@mcp.tool()
def set_mixer_level(track_index: int, level: float) -> Dict[str, Any]:
    """Sets mixer track volume level (0.0 to 1.0) via MIDI command 7."""
    if not 0 <= track_index <= 125: # FL Mixer tracks 0(Current)-125
        return {"status": "error", "message": "Mixer track index must be between 0 and 125"}
    if not 0.0 <= level <= 1.0:
        return {"status": "error", "message": "Level must be between 0.0 and 1.0"}

    logger.info(f"Sending command to set mixer track {track_index} level to {level:.2f} (Cmd 7)...")
    # device_FLStudioMCPController.py: Cmd 7 uses 'track' (CC121) and 'value' (CC123).
    level_param_value = int(level * 127) # Scale 0.0-1.0 to 0-127

    result = send_command(command_type=7, params={"track": track_index, "value": level_param_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send set mixer level command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Command to set mixer track {track_index} level to {level:.2f} sent."}


@mcp.tool()
def add_audio_effect(track_index: int, effect_type_or_name: str) -> Dict[str, Any]:
    """Adds an audio effect to a mixer track via MIDI command 10."""
    if not 0 <= track_index <= 125:
         return {"status": "error", "message": "Mixer track index must be between 0 and 125"}

    logger.info(f"Sending command to add effect '{effect_type_or_name}' to track {track_index} (Cmd 10)...")
    # device_FLStudioMCPController.py: Cmd 10 uses 'track' (CC121) and 'instrument' (CC125, repurposed) for effect type value.
    # Requires mapping from name/type string to an int value (0-127) understood by FL script.
    effect_map = {"reverb": 1, "delay": 2, "eq": 3, "compressor": 4, "limiter": 0} # Example mapping
    effect_param_value = effect_map.get(effect_type_or_name.lower(), -1)

    if effect_param_value == -1:
        logger.warning(f"Unknown effect type '{effect_type_or_name}'. Attempting to send value 0 (default).")
        effect_param_value = 0

    result = send_command(command_type=10, params={"track": track_index, "instrument": effect_param_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send add audio effect command: {result.get('message')}")
        return result
    else:
         return {"status": "success", "message": f"Command to add effect '{effect_type_or_name}' to track {track_index} sent."}

@mcp.tool()
def add_midi_effect(track_index: int, effect_type_or_name: str) -> Dict[str, Any]:
    """(Not Implemented in FL Script) Attempts to add a MIDI effect via command 9."""
    # device_FLStudioMCPController.py notes Cmd 9 is not implemented.
    logger.warning(f"Attempting to call 'add_midi_effect' (Cmd 9), but it's noted as not implemented in the FL script.")
    # We can still send the command, but expect an error or no action.
    # Let's return an error immediately from the server side.
    # If you implement Cmd 9 in FL, update this tool.
    return {"status": "error", "message": "Command type 9 (Add MIDI Effect) is not implemented in the FL Studio script."}
    # If you were to send it:
    # effect_param_value = 0 # Map effect name to value if implemented
    # result = send_command(command_type=9, params={"track": track_index, "instrument": effect_param_value}, wait_for_feedback=False)
    # return result


# --- Creation / Generation Tools ---

@mcp.tool()
def create_notes(channel_index: int, clear_first: bool = False) -> Dict[str, Any]:
    """(Experimental) Creates notes or clears notes on a channel via command 1."""
    logger.info(f"Sending command to {'clear notes on' if clear_first else 'create notes for'} channel {channel_index} (Cmd 1)...")
    # device_FLStudioMCPController.py: Cmd 1 uses 'track' (CC121) and 'action' (CC124, >0 means clear).
    # The FL script notes this command is experimental / not fully implemented for creation.
    action_value = 1 if clear_first else 0 # 1 = clear, 0 = create (though creation logic might be missing)

    result = send_command(command_type=1, params={"track": channel_index, "action": action_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send create/clear notes command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Command to {'clear' if clear_first else 'create'} notes for channel {channel_index} sent (Note: FL script implementation might be limited)."}


@mcp.tool()
def create_chord_progression(progression: List[str], channel_index: int = 0, octave: int = 4) -> Dict[str, Any]:
    """Creates a chord progression via command 8."""
    logger.info(f"Sending command to create chord progression {progression} on channel {channel_index} (Cmd 8)...")
    # device_FLStudioMCPController.py: Cmd 8 is defined but noted as needing direct note events.
    # The original server.py code had direct note event logic here instead of sending command 8.
    # Stick with sending Command 8 and let the FL script handle it (even if limited).
    # We need to decide how to pass the progression data. Sending complex lists via CC is hard.
    # Option 1: Cmd 8 just triggers a *predefined* progression in FL script.
    # Option 2: Cmd 8 takes parameters for simple progression (e.g., root, type, count).
    # Option 3: Ignore Cmd 8 and use direct play_note calls (like original server.py).
    # Let's assume Option 1 for now - Cmd 8 triggers *something* in FL.
    # We might pass the channel index. Let's use 'track'.
    # We'll skip sending the actual progression list via CCs.

    # This tool will likely need refinement based on how Cmd 8 is actually implemented in FL.
    result = send_command(command_type=8, params={"track": channel_index}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send create chord progression command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Command to create chord progression on channel {channel_index} sent (Note: FL script implementation details matter)."}

@mcp.tool()
def create_track(track_type: str = "instrument") -> Dict[str, Any]:
    """(Not Implemented in FL Script) Creates a new track via command 2."""
     # device_FLStudioMCPController.py notes Cmd 2 is not implemented.
    logger.warning(f"Attempting to call 'create_track' (Cmd 2), but it's noted as not implemented in the FL script.")
    # Return error immediately.
    return {"status": "error", "message": "Command type 2 (Create Track) is not implemented in the FL Studio script."}
    # If you were to send it:
    # type_map = {"instrument": 0, "audio": 1, "automation": 2} # Example mapping
    # type_value = type_map.get(track_type.lower(), 0)
    # result = send_command(command_type=2, params={"type": type_value}, wait_for_feedback=False)
    # return result


@mcp.tool()
def load_instrument(instrument_name_or_type: str, channel_index: Optional[int] = None) -> Dict[str, Any]:
    """(Not Implemented in FL Script) Loads an instrument via command 3."""
    # device_FLStudioMCPController.py notes Cmd 3 is not implemented.
    logger.warning(f"Attempting to call 'load_instrument' (Cmd 3), but it's noted as not implemented in the FL script.")
    return {"status": "error", "message": "Command type 3 (Load Instrument) is not implemented in the FL Studio script."}
    # If you were to send it:
    # instrument_map = {"piano": 1, "bass": 2, "drum": 3, "synth": 4} # Example mapping
    # instrument_value = instrument_map.get(instrument_name_or_type.lower(), 0)
    # params = {"instrument": instrument_value}
    # if channel_index is not None:
    #     params["track"] = channel_index # Use 'track' (CC121) if specified
    # result = send_command(command_type=3, params=params, wait_for_feedback=False)
    # return result

# --- Visual/UI Tools ---

@mcp.tool()
def randomize_channel_colors(selected_only: bool = False) -> Dict[str, Any]:
    """Randomizes channel colors via command 11."""
    logger.info(f"Sending command to randomize colors for {'selected' if selected_only else 'all'} channels (Cmd 11)...")
    # device_FLStudioMCPController.py: Cmd 11 uses 'action' param (we can use 0 for all, 1 for selected).
    action_value = 1 if selected_only else 0

    result = send_command(command_type=11, params={"action": action_value}, wait_for_feedback=False)

    if result.get("status") != "success":
        logger.error(f"Failed to send randomize colors command: {result.get('message')}")
        return result
    else:
        return {"status": "success", "message": f"Command to randomize colors for {'selected' if selected_only else 'all'} channels sent."}


# --- Main Execution ---
def main():
    """Initializes ports and starts the MCP server."""
    logger.info("Starting FL Studio MCP Server...")
    # Ensure ports seem okay before starting listener and server
    if output_port is None:
         logger.critical("Output MIDI port not initialized. Server cannot start.")
         return
    if input_port_name is None:
         logger.warning("Input MIDI port name not found. Feedback listener will not start.")
         # Allow server to start without feedback if desired, or return here to enforce feedback.
         # return # Uncomment this line to prevent server start without feedback port

    start_midi_listener() # Start the listener thread

    try:
        logger.info("Running MCP server...")
        mcp.run() # This blocks until MCP stops (e.g., via its own shutdown mechanism or exception)
        logger.info("MCP server loop finished.")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down server.")
    except Exception as e:
        logger.exception("An unexpected error occurred in the main server loop.")
    finally:
        logger.info("Initiating server shutdown sequence...")
        # Cleanup (closing ports, stopping threads) is handled by atexit handlers
        logger.info("Server shutdown sequence finished.")

if __name__ == "__main__":
    main()