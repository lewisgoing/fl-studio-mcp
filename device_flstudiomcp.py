# device/flstudio_mcp.py
# name=FL Studio MCP Bridge (SysEx v2)
# url=https://github.com/your-repo/flstudio-mcp-iac # Update URL

"""
FL Studio MIDI Script for MCP Integration using SysEx Protocol v2.
Receives commands via SysEx, interacts with FL Studio API, sends responses via SysEx.
"""

# Standard FL Studio API imports
import midi
import device
import channels
import patterns
import transport
import mixer
import plugins
import ui
import general
import arrangement # Import if needed for arrangement commands

# Standard Python imports
import time
import json # Only used if needed beyond protocol handling
import random # For randomize colors example
import math   # For randomize colors example
import logging # Use standard logging if possible
import traceback # For detailed error logging
from typing import Dict, Any, Optional, List, Tuple # Added for type hinting

# --- Configuration ---
DEBUG = True # Enable/disable detailed logging via print/hints
MAX_EFFECT_SLOTS = 10 # Define max effect slots per mixer track (FL standard)

# --- Import Shared Protocol ---
# Assuming 'shared' is accessible relative to this script's location
try:
    from shared.protocols import Command as SharedCommand, encode_sysex, decode_sysex, SYSEX_HEADER, SYSEX_END
except ImportError as e:
    print(f"[MCP Device Error] Failed to import shared protocols: {e}. Ensure 'shared' directory is accessible.")
    # Define dummy Command class and functions with matching (but basic) signatures
    # to satisfy type checkers if the import fails.
    class Command:
        RESPONSE_ERROR = 0x71
        # Add other command IDs used in this script if necessary for fallback logic
        GET_CHANNEL_NAMES = 0x10
        GET_CHANNEL_NAME_BY_INDEX = 0x11
        # ... etc.
    # Fix: Make dummy signatures match the real ones more closely using Any
    def encode_sysex(command_id: Any, data: Any = None) -> bytes: return b''
    def decode_sysex(message: Any) -> Optional[Dict[str, Any]]: return None
    SYSEX_HEADER = b''
    SYSEX_END = 0

# --- State (Optional - Keep minimal) ---
last_known_tempo: float = 120.0

# --- Logging ---
def log(message: str):
    """Simple logger for the device script."""
    if DEBUG:
        prefix = "[FL Device]"
        # Try using FL's hint mechanism for visibility
        try:
            # Check if ui module was imported successfully before using it
            if 'ui' in globals() and ui:
                 ui.setHintMsg(f"{prefix} {message}")
        except Exception: # Catch potential errors from ui.setHintMsg
            pass
        print(f"{prefix} {message}")

# --- Helper Functions ---
def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[float, float, float]:
    """Convert HSV color to RGB floats (0-1). Needed for randomize_colors."""
    if s == 0.0: return v, v, v
    h *= 6.0
    i = int(h)
    f = h - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0: return v, t, p
    if i == 1: return q, v, p
    if i == 2: return p, v, t
    if i == 3: return p, q, v
    if i == 4: return t, p, v
    if i == 5: return v, p, q
    return v,v,v # Should not happen

# --- SysEx Communication ---
def send_response(command_id: int, response_to: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
    """
    Encodes and sends a SysEx response back to the server.
    Includes the original request ID if provided.
    """
    response_payload: Dict[str, Any] = data.copy() if data else {}
    if response_to is not None:
        response_payload["response_to"] = response_to # Link response to request

    try:
        # Fix 7-9, 18-20: Check device module availability first
        if 'device' in globals() and device:
             # Fix: Corrected function name device.isAssigned()
             if device.isAssigned():
                  response_message = encode_sysex(command_id, response_payload)
                  if response_message:
                       # Fix 10-12: Corrected function name device.midiOutSysex()
                       device.midiOutSysex(response_message)
                       # Limit log length for potentially large data payloads
                       data_str = str(response_payload)
                       if len(data_str) > 100: data_str = data_str[:100] + "..."
                       log(f"Sent Response: Cmd={hex(command_id)}, Data={data_str}")
                  else:
                       log(f"Error: Failed to encode SysEx for response Cmd={hex(command_id)}")
             else:
                  log("Error: Device port not assigned, cannot send response.")
        else:
             log("Error: FL Studio 'device' module not available.")
    except Exception as e:
        log(f"Error sending SysEx response: {e}")
        traceback.print_exc()


def handle_sysex_command(decoded_message: Dict):
    """Processes incoming commands received via SysEx from the server."""
    if not decoded_message:
        log("Error: Received empty decoded message.")
        return

    command_id: Optional[int] = decoded_message.get("command_id")
    # Ensure data is always a dict, default to empty dict if missing or not a dict
    data: Dict[str, Any] = decoded_message.get("data", {}) if isinstance(decoded_message.get("data"), dict) else {}
    request_id: Optional[int] = data.get("request_id") if isinstance(data.get("request_id"), int) else None

    # Fix 13-15, 54-59: Use safe formatting for potentially None command_id
    log(f"Handling Command: {command_id:#04x}, ReqID: {request_id}, Data: {data}")

    try:
        # Fix 16-17, 21-44: Explicitly type hint result_data
        result_data: Optional[Dict[str, Any]] = None # Data to be sent back on success

        if command_id is None:
             raise ValueError("Command ID missing in decoded message")

        # === Channel Commands ===
        if command_id == SharedCommand.GET_CHANNEL_NAMES:
            names = [channels.getChannelName(i, False) for i in range(channels.channelCount(False))]
            result_data = {"names": names}

        elif command_id == SharedCommand.GET_CHANNEL_NAME_BY_INDEX:
            index = data.get("index")
            # Add type check for index
            if isinstance(index, int) and 0 <= index < channels.channelCount(False):
                name = channels.getChannelName(index, False)
                result_data = {"index": index, "name": name}
            else:
                raise ValueError(f"Invalid or missing channel index: {index}")

        elif command_id == SharedCommand.SET_CHANNEL_COLOR:
            index = data.get("index")
            color = data.get("color")
            # Add type checks
            if isinstance(index, int) and isinstance(color, int) and 0 <= index < channels.channelCount(False):
                 channels.setChannelColor(index, color, False)
                 result_data = {"index": index, "color": color} # Acknowledge success
            else:
                 raise ValueError("Missing or invalid type for index or color parameter")

        elif command_id == SharedCommand.RANDOMIZE_COLORS:
             selected_only = data.get("selected_only", False)
             count = 0
             total_channels = channels.channelCount(False)
             if total_channels > 0:
                 for i in range(total_channels):
                      if selected_only and not channels.isChannelSelected(i, False):
                          continue
                      # Fix 18-20: Use helper function hsv_to_rgb defined above
                      hue = random.random()
                      r_f, g_f, b_f = hsv_to_rgb(hue, 0.9, 0.9)
                      r, g, b = int(r_f * 255), int(g_f * 255), int(b_f * 255)
                      color = (b << 16) | (g << 8) | r
                      channels.setChannelColor(i, color, False)
                      count += 1
                 result_data = {"count": count, "selected_only": selected_only}
             else:
                 result_data = {"count": 0, "selected_only": selected_only} # Success, but no channels

        elif command_id == SharedCommand.GET_CHANNEL_COUNT:
             count = channels.channelCount(False)
             result_data = {"count": count}

        elif command_id == SharedCommand.IS_CHANNEL_SELECTED:
             index = data.get("index")
             if isinstance(index, int) and 0 <= index < channels.channelCount(False):
                  selected = channels.isChannelSelected(index, False)
                  result_data = {"index": index, "selected": selected}
             else:
                  raise ValueError(f"Invalid or missing channel index: {index}")

        elif command_id == SharedCommand.SELECT_CHANNEL:
             index = data.get("index")
             value = data.get("value", -1) # -1=toggle, 0=deselect, 1=select
             if isinstance(index, int) and isinstance(value, int) and value in [-1, 0, 1] and 0 <= index < channels.channelCount(False):
                  channels.selectChannel(index, value, False)
                  result_data = {"index": index, "value": value}
             else:
                  raise ValueError(f"Invalid or missing channel index or value: {index}, {value}")

        elif command_id == SharedCommand.GET_CHANNEL_VOLUME:
             index = data.get("index")
             if isinstance(index, int) and 0 <= index < channels.channelCount(False):
                  volume = channels.getChannelVolume(index, False, False) # Mode 0 = normalized
                  result_data = {"index": index, "volume": volume}
             else:
                  raise ValueError(f"Invalid or missing channel index: {index}")

        elif command_id == SharedCommand.SET_CHANNEL_VOLUME:
             index = data.get("index")
             volume = data.get("volume") # Expect float/int 0.0-1.0
             if isinstance(index, int) and isinstance(volume, (int, float)) and 0 <= index < channels.channelCount(False):
                  volume_f = float(volume)
                  channels.setChannelVolume(index, max(0.0, min(1.0, volume_f)), midi.PIM_None, False)
                  result_data = {"index": index, "volume": volume_f}
             else:
                  raise ValueError("Missing or invalid type for index or volume parameter")

        # === Add GET/SET for Pan, Mute, Solo similarly, including type checks ===


        # === Mixer Commands ===
        elif command_id == SharedCommand.SET_MIXER_LEVEL:
             track = data.get("track")
             level = data.get("level") # Expect float/int 0.0-1.0
             if isinstance(track, int) and isinstance(level, (int, float)) and 0 <= track < mixer.trackCount():
                  level_f = float(level)
                  mixer.setTrackVolume(track, max(0.0, min(1.0, level_f)))
                  result_data = {"track": track, "level": level_f}
             else:
                  raise ValueError("Missing or invalid type for track index or level parameter")

        elif command_id == SharedCommand.ADD_AUDIO_EFFECT:
             track = data.get("track")
             effect_name_or_id = data.get("effect") # Server sends name or identifier
             if isinstance(track, int) and isinstance(effect_name_or_id, str) and 0 <= track < mixer.trackCount():
                 # Fix 45-47: Correct function name findPluginIndex
                 plugin_index = plugins.findPluginIndex(effect_name_or_id)
                 if plugin_index == -1:
                      raise ValueError(f"Effect '{effect_name_or_id}' not found.")

                 # Find first empty slot
                 slot_index = -1
                 # Fix 48-50: Use a constant for max slots
                 for i in range(MAX_EFFECT_SLOTS):
                      if mixer.getTrackPluginId(track, i) == 0: # 0 means empty slot
                           slot_index = i
                           break
                 if slot_index == -1:
                      raise RuntimeError(f"No free effect slots on track {track}")

                 # Fix 51-53: Use setTrackPluginId to load into slot
                 # Note: This assigns the plugin ID, it might not trigger a full "load" in all cases.
                 # More complex loading might need REC events or other API calls.
                 mixer.setTrackPluginId(track, slot_index, plugin_index)
                 # Verify the plugin name after setting ID
                 time.sleep(0.05) # Short delay maybe needed for API to update
                 loaded_name = plugins.getPluginName(plugin_index) # Get general name
                 actual_plugin_id_in_slot = mixer.getTrackPluginId(track, slot_index)

                 if actual_plugin_id_in_slot == plugin_index:
                     result_data = {"track": track, "slot": slot_index, "effect_name": loaded_name, "plugin_index": plugin_index}
                 else:
                     raise RuntimeError(f"Failed to set plugin ID for '{effect_name_or_id}' on track {track} slot {slot_index}")
             else:
                  raise ValueError("Missing or invalid type for track index or effect identifier")

        elif command_id == SharedCommand.GET_MIXER_TRACK_COUNT:
             count = mixer.trackCount()
             result_data = {"count": count}

        elif command_id == SharedCommand.GET_MIXER_LEVEL:
             track = data.get("track")
             if isinstance(track, int) and 0 <= track < mixer.trackCount():
                  level = mixer.getTrackVolume(track)
                  result_data = {"track": track, "level": level}
             else:
                  raise ValueError(f"Invalid or missing track index: {track}")


        # === Transport Commands ===
        elif command_id == SharedCommand.TRANSPORT_CONTROL:
             action = data.get("action")
             if isinstance(action, str):
                  action_lower = action.lower()
                  if action_lower == "play": transport.start()
                  elif action_lower == "stop": transport.stop()
                  elif action_lower == "record": transport.record()
                  elif action_lower == "toggle_play":
                      if transport.isPlaying(): transport.stop()
                      else: transport.start()
                  else:
                      raise ValueError(f"Invalid transport action: {action}")
                  result_data = {"action": action_lower, "is_playing": transport.isPlaying()}
             else:
                  raise ValueError("Missing or invalid type for action parameter")

        elif command_id == SharedCommand.SET_TEMPO:
            bpm = data.get("bpm")
            if isinstance(bpm, (int, float)):
                 bpm_value = float(bpm)
                 tempo_internal = int(max(20.0, min(999.0, bpm_value)) * 1000)
                 general.processRECEvent(midi.REC_Tempo, tempo_internal, midi.REC_Control | midi.REC_UpdateControl)
                 time.sleep(0.05) # Allow FL to process
                 actual_bpm = mixer.getCurrentTempo() / 1000
                 result_data = {"requested_bpm": bpm_value, "actual_bpm": actual_bpm}
            else:
                 raise ValueError("Missing or invalid type for bpm parameter")

        elif command_id == SharedCommand.GET_TEMPO:
            bpm = mixer.getCurrentTempo() / 1000
            result_data = {"bpm": bpm}

        elif command_id == SharedCommand.GET_IS_PLAYING:
            playing = transport.isPlaying()
            result_data = {"is_playing": playing}

        elif command_id == SharedCommand.SELECT_PATTERN:
            pattern_num = data.get("pattern") # Expect 1-based index
            if isinstance(pattern_num, int):
                 pattern_index = pattern_num - 1 # Convert to 0-based for API
                 if 0 <= pattern_index < patterns.patternCount():
                      patterns.jumpToPattern(pattern_index)
                      result_data = {"pattern": pattern_num}
                 else:
                      raise ValueError(f"Invalid pattern number: {pattern_num}")
            else:
                 raise ValueError("Missing or invalid type for pattern number")

        elif command_id == SharedCommand.GET_CURRENT_PATTERN:
            current_pattern = patterns.patternNumber() # Gets 1-based index
            result_data = {"pattern": current_pattern}


        # === Add handlers for other Command IDs here ===


        else:
            # Unknown command
            raise ValueError(f"Unknown command ID: {command_id:#04x}")

        # If we reach here, the command was processed successfully
        send_response(SharedCommand.RESPONSE_SUCCESS, response_to=request_id, data=result_data)

    except Exception as e:
        # Fix 54-59: Use safe formatting for potentially None command_id
        log(f"!!! Error processing command {command_id:#04x}: {e}")
        traceback.print_exc() # Print full traceback to FL console if possible
        # Send an error response back to the server
        send_response(SharedCommand.RESPONSE_ERROR, response_to=request_id, data={"message": str(e)})


# --- FL Studio Event Handlers ---

def OnInit():
    """Called when the script is initialized by FL Studio."""
    global last_known_tempo
    log("FL Studio MCP Bridge (SysEx v2) Initializing...")
    try:
        # Fix 60-65: Corrected function names getPortNumber() and getName()
        port_num = device.getPortNumber() if ('device' in globals() and device) else 'N/A'
        dev_name = device.getName() if ('device' in globals() and device) else 'N/A'
        log(f"Device Port: {port_num}, Name: {dev_name}")
        if 'mixer' in globals() and mixer:
             last_known_tempo = mixer.getCurrentTempo() / 1000
        else:
             last_known_tempo = 120.0
    except Exception as e:
        log(f"Error during OnInit: {e}")
        traceback.print_exc()
    log("Initialization Complete.")


def OnDeInit():
    """Called when the script is unloaded by FL Studio."""
    log("FL Studio MCP Bridge Deinitializing.")


def OnMidiMsg(event):
    """Handles incoming MIDI messages from the assigned MIDI port."""
    # Fix 66-68: Use correct constant MIDI_SYSTEM_EXCLUSIVE
    if event.midiId == midi.MIDI_SYSTEM_EXCLUSIVE:
        # Check if it starts with our header
        if event.sysex and event.sysex.startswith(SYSEX_HEADER):
            log(f"SysEx Received: {event.sysex.hex()}") # Log raw hex
            decoded = decode_sysex(event.sysex)
            if decoded:
                handle_sysex_command(decoded)
            else:
                log("Failed to decode received SysEx matching header.")
            event.handled = True
        else:
            event.handled = False # Let FL handle other SysEx
        return # Return after handling SysEx decision

    # Let FL Studio handle any other unhandled messages by default
    event.handled = False

def OnIdle():
    """Called periodically by FL Studio. Use for background tasks."""
    global last_known_tempo
    try:
        # Check if mixer module is available
        if 'mixer' in globals() and mixer:
            current_tempo = mixer.getCurrentTempo() / 1000
            if abs(current_tempo - last_known_tempo) > 0.01:
                log(f"Tempo changed locally to {current_tempo:.2f}")
                send_response(SharedCommand.ASYNC_UPDATE, data={"tempo": current_tempo})
                last_known_tempo = current_tempo
    except Exception as e:
        log(f"Error in OnIdle: {e}")
        # Avoid continuous errors, maybe disable the check after an error?


def OnWaitingForInput():
    """Called when FL Studio is idle and waiting for user input."""
    pass


# --- Optional: Direct function calls for debugging/testing from FL script console ---
def TestGetNames():
    log("Testing Get Channel Names...")
    handle_sysex_command({"command_id": SharedCommand.GET_CHANNEL_NAMES, "data": {"request_id": 999}})

def TestSetColor(index=0, color=0xFF0000):
    log(f"Testing Set Color {hex(color)} for index {index}...")
    handle_sysex_command({"command_id": SharedCommand.SET_CHANNEL_COLOR, "data": {"index": index, "color": color, "request_id": 998}})

def TestTransport(action="play"):
     log(f"Testing Transport {action}...")
     handle_sysex_command({"command_id": SharedCommand.TRANSPORT_CONTROL, "data": {"action": action, "request_id": 997}})