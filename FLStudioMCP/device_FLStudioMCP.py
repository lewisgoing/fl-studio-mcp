# name=FL Studio MCP (User)
# url=https://github.com/lewisgoing/fl-studio-mcp (Optional: Add your repo link here)

"""
FL Studio MIDI Remote Script for MCP Integration.
This script runs inside FL Studio and listens for commands from the external MCP server via a socket.
"""

import socket
import threading
import json
import time
import traceback

# Import FL Studio API modules - Add more as needed
import device
import channels
import mixer
import patterns
import transport
import ui # Added for potential future use (e.g., showing messages)
import general # Added for potential future use

# --- Configuration ---
HOST = 'localhost'
PORT = 9877 # Port the MCP server will connect to
# --- End Configuration ---

# Global state
server_socket = None
server_thread = None
client_handler_thread = None
stop_server_flag = threading.Event()
is_connected = False

def log_message(message):
    """Logs a message to the FL Studio Script output window."""
    print(f"FLStudioMCP_Script: {message}")

# --- Socket Server Implementation ---

def handle_client_connection(client_socket):
    """Handles communication with the connected MCP server."""
    global is_connected
    log_message("MCP Server connected.")
    is_connected = True
    buffer = ''
    client_socket.settimeout(1.0) # Timeout for recv

    while not stop_server_flag.is_set():
        try:
            data = client_socket.recv(8192)
            if not data:
                log_message("MCP Server disconnected.")
                break # Connection closed by peer

            buffer += data.decode('utf-8')

            # Process complete JSON messages
            while True:
                try:
                    command, index = json.JSONDecoder().raw_decode(buffer)
                    buffer = buffer[index:].lstrip() # Remove processed message and leading whitespace
                    log_message(f"Received command: {command.get('type', 'unknown')}")
                    response = process_command(command)
                    client_socket.sendall(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    # Not a complete JSON message in buffer yet
                    break
                except Exception as e:
                    log_message(f"Error processing/sending response: {e}")
                    log_message(traceback.format_exc())
                    # Attempt to send error back
                    error_response = {"status": "error", "message": f"Error in FL Script: {e}"}
                    try:
                        client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                    except Exception as send_err:
                         log_message(f"Failed to send error response: {send_err}")
                    # Decide if error is fatal for this connection
                    # For now, we continue, but might want to break
                    buffer = '' # Clear buffer on error

        except socket.timeout:
            continue # Just loop again to check stop_server_flag
        except socket.error as e:
            log_message(f"Socket error: {e}")
            break # Connection lost
        except Exception as e:
            log_message(f"Unhandled error in client handler: {e}")
            log_message(traceback.format_exc())
            break # General error, close connection

    is_connected = False
    try:
        client_socket.close()
    except socket.error:
        pass
    log_message("Client handler stopped.")


def start_listening_server():
    """Starts the socket server to listen for the MCP server."""
    global server_socket, stop_server_flag, client_handler_thread
    stop_server_flag.clear()

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1) # Listen for only one connection (the MCP server)
        server_socket.settimeout(1.0) # Timeout for accept
        log_message(f"Listening for MCP server on {HOST}:{PORT}...")

        while not stop_server_flag.is_set():
            try:
                client_socket, addr = server_socket.accept()
                log_message(f"Accepted connection from {addr}")

                # If another client handler is running, stop it (shouldn't happen with listen(1))
                if client_handler_thread and client_handler_thread.is_alive():
                     log_message("Stopping previous client handler...")
                     # This part is tricky, might need a more robust way to signal previous thread
                     # For now, we rely on the new connection replacing the old logic focus

                client_handler_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
                client_handler_thread.daemon = True
                client_handler_thread.start()

            except socket.timeout:
                continue # Check stop_server_flag again
            except Exception as e:
                log_message(f"Error accepting connection: {e}")
                time.sleep(1) # Avoid busy-looping on persistent errors

    except Exception as e:
        log_message(f"Server socket error: {e}")
    finally:
        if server_socket:
            try:
                server_socket.close()
            except socket.error:
                pass
        server_socket = None
        log_message("Socket server stopped.")


# --- Command Processing ---

def process_command(command):
    """Processes a command received from the MCP server."""
    command_type = command.get("type", "")
    params = command.get("params", {})
    response = {"status": "success", "result": {}}

    # Wrap FL Studio API calls in try-except blocks
    try:
        # --- Add Command Handlers Here ---
        if command_type == "get_session_info":
            response["result"] = get_session_info_handler()
        elif command_type == "get_track_info":
            response["result"] = get_track_info_handler(params)
        elif command_type == "create_midi_track":
             response["result"] = create_midi_track_handler(params)
        elif command_type == "set_track_name":
             response["result"] = set_track_name_handler(params)
        elif command_type == "create_clip":
             response["result"] = create_clip_handler(params)
        elif command_type == "add_notes_to_clip":
             response["result"] = add_notes_to_clip_handler(params)
        elif command_type == "set_clip_name":
             response["result"] = set_clip_name_handler(params)
        elif command_type == "set_tempo":
             response["result"] = set_tempo_handler(params)
        elif command_type == "fire_clip":
             response["result"] = fire_clip_handler(params)
        elif command_type == "stop_clip":
             response["result"] = stop_clip_handler(params)
        elif command_type == "start_playback":
             response["result"] = start_playback_handler(params)
        elif command_type == "stop_playback":
             response["result"] = stop_playback_handler(params)
        elif command_type == "load_instrument_or_effect":
             response["result"] = load_instrument_handler(params)

        # Add more command handlers based on fl_mcp_server/server.py tools
        # Example:
        # elif command_type == "some_other_action":
        #    required_param = params.get("required_param")
        #    if required_param is None:
        #        raise ValueError("Missing required_param")
        #    # Call FL Studio API: some_module.some_function(required_param)
        #    response["result"] = {"message": "Action completed"}

        else:
            raise NotImplementedError(f"Command type '{command_type}' not implemented.")

    except Exception as e:
        log_message(f"Error processing command '{command_type}': {e}")
        log_message(traceback.format_exc())
        response["status"] = "error"
        response["message"] = str(e)

    return response

# --- Individual Command Handlers ---
# (These functions wrap the actual FL Studio API calls)

def get_session_info_handler():
    tempo = transport.getSongTempo()
    # FL master track is index 0
    master_volume_db = mixer.getTrackVolume(0, 1) # Get dB value
    master_pan = mixer.getTrackPan(0)
    count = channels.channelCount()

    # Get time signature (less direct in API, might need to assume or find workarounds)
    sig_num, sig_den = transport.getTimeSig()

    return {
        "tempo": tempo,
        "signature_numerator": sig_num if sig_num else 4,
        "signature_denominator": sig_den if sig_den else 4,
        "track_count": count,
        "master_track": {
            "name": "Master",
            "volume_db": master_volume_db,
             "pan": master_pan, # Added pan
        }
    }

def get_track_info_handler(params):
    track_index = params.get("track_index")
    if track_index is None or track_index < 0 or track_index >= channels.channelCount():
        raise ValueError(f"Invalid track_index: {track_index}")

    name = channels.getChannelName(track_index)
    is_muted = channels.isChannelMuted(track_index) == 1
    is_solo = channels.isChannelSolo(track_index) == 1
    color_tuple = channels.getChannelColor(track_index, 1) # Get RGB tuple
    color_hex = '#%02x%02x%02x' % color_tuple if color_tuple else '#AAAAAA'

    mixer_track_index = channels.getTargetFxTrack(track_index)
    volume_db = mixer.getTrackVolume(mixer_track_index, 1) if mixer_track_index >= 0 else 0.0
    pan = mixer.getTrackPan(mixer_track_index) if mixer_track_index >= 0 else 0.0

    # Basic check for instrument type (needs improvement)
    plugin_name = channels.getChannelPluginName(track_index)
    is_midi = True # Assume MIDI for now
    is_audio = False # Assume not audio

    # Check patterns using this channel
    patterns_info = []
    num_patterns = patterns.patternCount()
    for i in range(num_patterns):
        if channels.isChannelUsedInPattern(i, track_index):
            patterns_info.append({
                "index": i,
                "name": patterns.getPatternName(i)
            })

    return {
        "index": track_index,
        "name": name,
        "is_audio_track": is_audio,
        "is_midi_track": is_midi,
        "plugin_name": plugin_name,
        "mute": is_muted,
        "solo": is_solo, # Added solo status
        "volume_db": volume_db,
        "panning": pan,
        "color_hex": color_hex, # Added color
        "mixer_track_index": mixer_track_index,
        "patterns": patterns_info
    }

def create_midi_track_handler(params):
    # FL specific: create a channel
    # The 'index' param from MCP might mean insert position, hard in FL channel rack
    channel_index = channels.addChannel("Sampler") # Default to Sampler
    new_name = f"MCP Channel {channel_index+1}" # Use 1-based for name
    channels.setChannelName(channel_index, new_name)
    # Optionally set color, route to mixer, load default instrument
    return {"index": channel_index, "name": new_name}

def set_track_name_handler(params):
    track_index = params.get("track_index")
    name = params.get("name")
    if track_index is None or track_index < 0 or track_index >= channels.channelCount():
        raise ValueError(f"Invalid track_index: {track_index}")
    if name is None:
        raise ValueError("Missing name parameter")
    channels.setChannelName(track_index, name)
    return {"index": track_index, "name": name}

def create_clip_handler(params):
    # track_index = params.get("track_index") # Less relevant for creating FL patterns
    pattern_index = params.get("clip_index") # Use clip_index as pattern_index
    length = params.get("length", 4.0) # Length in beats

    if pattern_index is None or pattern_index < 0:
         # If index is -1 or omitted, create a new pattern
         pattern_index = patterns.addPattern("MCP Pattern")
    elif pattern_index >= patterns.patternCount():
        # Create patterns up to the specified index
        while patterns.patternCount() <= pattern_index:
             patterns.addPattern(f"Pattern {patterns.patternCount()+1}") # Default name
    # else: use existing pattern_index

    # Set length (API might be limited here, might need to use Piano Roll access)
    # patterns.setPatternLength(pattern_index, length_in_some_unit) # Check API if exists
    current_len = patterns.getPatternLength(pattern_index)

    return {"pattern_index": pattern_index, "name": patterns.getPatternName(pattern_index), "length_beats": current_len} # Return current length

def add_notes_to_clip_handler(params):
    # track_index = params.get("track_index")
    pattern_index = params.get("pattern_index")
    notes = params.get("notes", [])
    if pattern_index is None or pattern_index < 0 or pattern_index >= patterns.patternCount():
        raise ValueError(f"Invalid pattern_index: {pattern_index}")

    # NOTE: FL Studio's direct note manipulation via script is limited.
    # This requires accessing the Piano Roll, which is complex.
    # This handler is a placeholder and won't actually add notes without
    # significant additional work using undocumented or advanced techniques.
    log_message("Note addition requested, but currently not implemented due to API limitations.")

    return {"notes_processed": 0, "message": "Note addition not implemented"}

def set_clip_name_handler(params):
    # track_index = params.get("track_index") # Not needed for pattern name
    pattern_index = params.get("pattern_index")
    name = params.get("name")
    if pattern_index is None or pattern_index < 0 or pattern_index >= patterns.patternCount():
        raise ValueError(f"Invalid pattern_index: {pattern_index}")
    if name is None:
        raise ValueError("Missing name parameter")
    patterns.setPatternName(pattern_index, name)
    return {"pattern_index": pattern_index, "name": name}

def set_tempo_handler(params):
    tempo = params.get("tempo")
    if tempo is None or tempo <= 0:
         raise ValueError(f"Invalid tempo: {tempo}")
    transport.setSongTempo(tempo, 1) # 1 = Set immediately
    return {"tempo": transport.getSongTempo()}

def fire_clip_handler(params):
    # track_index = params.get("track_index") # Not directly used
    pattern_index = params.get("pattern_index")
    if pattern_index is None or pattern_index < 0 or pattern_index >= patterns.patternCount():
        raise ValueError(f"Invalid pattern_index: {pattern_index}")
    # Ensure FL is in Pattern mode, select pattern, start playback
    if general.getEditMode() != 1: # 1 = Pattern mode
        general.setEditMode(1)
    patterns.setPatternNumber(pattern_index + 1) # API uses 1-based index
    if not transport.isPlaying():
        transport.start()
    return {"fired_pattern": pattern_index}

def stop_clip_handler(params):
    # track_index = params.get("track_index") # Not directly used
    # pattern_index = params.get("pattern_index") # Not directly used
    # Simplest way is to just stop transport
    if transport.isPlaying():
        transport.stop()
    return {"stopped": True}

def start_playback_handler(params):
    if not transport.isPlaying():
        transport.start()
    return {"playing": transport.isPlaying()}

def stop_playback_handler(params):
    if transport.isPlaying():
        transport.stop()
    return {"playing": transport.isPlaying()}

def load_instrument_handler(params):
    track_index = params.get("track_index")
    instrument_name = params.get("instrument_name")
    if track_index is None or track_index < 0 or track_index >= channels.channelCount():
        raise ValueError(f"Invalid track_index: {track_index}")
    if not instrument_name:
         raise ValueError("Missing instrument_name parameter")

    # FL API requires finding the plugin index first
    plugin_index = channels.findPlugin(instrument_name, 1) # 1 = Generators
    if plugin_index == -1:
        plugin_index = channels.findPlugin(instrument_name, 0) # 0 = Effects (fallback?)

    if plugin_index != -1:
        # Replace the current plugin on the channel
        channels.replaceChannelPlugin(track_index, plugin_index)
        loaded_name = channels.getChannelPluginName(track_index)
        return {"loaded": True, "instrument_name": loaded_name}
    else:
        raise ValueError(f"Instrument '{instrument_name}' not found.")


# --- FL Studio Script Events ---

def OnInit():
    """Called when the script is loaded by FL Studio."""
    global server_thread, stop_server_flag
    log_message("Initializing...")
    stop_server_flag.clear()
    # Start the server thread
    server_thread = threading.Thread(target=start_listening_server)
    server_thread.daemon = True
    server_thread.start()
    log_message("Script Initialized. Ready for MCP connection.")
    # Set a default device name (can be overridden by # name= line)
    # device.setName("FL Studio MCP Script") # Handled by #name=
    return 0 # Indicate success

def OnDeInit():
    """Called when the script is about to be unloaded."""
    global server_thread, stop_server_flag, server_socket, client_handler_thread
    log_message("Deinitializing...")
    stop_server_flag.set() # Signal threads to stop

    # Close server socket to interrupt accept()
    if server_socket:
        try:
            server_socket.close()
        except Exception as e:
             log_message(f"Error closing server socket: {e}")

    # Wait for threads to finish
    if server_thread and server_thread.is_alive():
        log_message("Waiting for server thread to stop...")
        server_thread.join(timeout=2.0)
    if client_handler_thread and client_handler_thread.is_alive():
         log_message("Waiting for client handler thread to stop...")
         client_handler_thread.join(timeout=2.0)

    log_message("Script Deinitialized.")
    return 0

def OnIdle():
    """Called periodically. Can be used for updates."""
    # Example: Update MCP server about connection status if needed
    pass

# Add other On... event handlers as needed (e.g., OnRefresh, OnMidiMsg)
# def OnRefresh(flags):
#     log_message(f"OnRefresh called with flags: {flags}")
#     # Potentially send updates to the MCP server if it's connected
#     if is_connected:
#         # Send relevant updates based on flags
#         pass

# def OnMidiMsg(eventData):
#    # Handle incoming MIDI if needed, maybe forward to MCP?
#    pass