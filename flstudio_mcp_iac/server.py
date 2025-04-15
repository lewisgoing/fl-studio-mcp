import mido
import json
import time
import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flstudio-mcp')

# Initialize the MCP server
mcp = FastMCP("flstudio-mcp")

# Configure MIDI port - we'll handle errors if the port isn't found
output_port = None
try:
    # Look for the IAC Driver port
    available_ports = mido.get_output_names()
    logger.info(f"Available MIDI ports: {available_ports}")
    
    for port in available_ports:
        if 'IAC Driver MCP Bridge' in port:
            output_port = mido.open_output(port)
            logger.info(f"Connected to MIDI port: {port}")
            break
    
    if output_port is None:
        # If exact name not found, try to find any IAC port
        for port in available_ports:
            if 'IAC' in port:
                output_port = mido.open_output(port)
                logger.info(f"Connected to MIDI port: {port}")
                break
        
        if output_port is None:
            logger.error("No IAC Driver port found. Please ensure the IAC Driver is properly configured.")
except Exception as e:
    logger.error(f"Error initializing MIDI: {e}")

# Define MIDI message encoding functions
def encode_note_on(note, velocity):
    """Create a note-on MIDI message."""
    return mido.Message('note_on', note=note, velocity=velocity)

def encode_note_off(note):
    """Create a note-off MIDI message."""
    return mido.Message('note_off', note=note)

def encode_cc(controller, value):
    """Create a control change MIDI message."""
    return mido.Message('control_change', control=controller, value=value)

# FL Studio uses a different approach for SysEx, adapting to use CC-based commands
def encode_command(command_type, params=None):
    """
    Encode a command as a series of MIDI messages using FL Studio's expected format.
    We're simplifying the protocol to better match FL Studio's handling capabilities.
    """
    messages = []
    
    # Command marker (CC 120 with value = command type)
    messages.append(encode_cc(120, command_type))
    
    # If we have parameters, encode them as simplified key-value pairs
    if params:
        for key, value in params.items():
            # Convert non-integer values to integers where possible
            if isinstance(value, float):
                # Scale floats between 0-1 to 0-127
                if 0 <= value <= 1:
                    value_int = int(value * 127)
                else:
                    value_int = int(min(127, max(0, value)))
            elif isinstance(value, bool):
                value_int = 127 if value else 0
            elif isinstance(value, str):
                # For strings, we just send the first char's ASCII value
                # (limited, but works for simple identifiers)
                value_int = ord(value[0]) % 128 if value else 0
            elif isinstance(value, int):
                value_int = min(127, max(0, value))
            else:
                value_int = 0
                
            # Encode parameter key using CC 121-125 range
            # This limits us to 5 parameters, but ensures compatibility
            if key == "track" or key == "channel":
                messages.append(encode_cc(121, value_int))
            elif key == "pattern" or key == "bpm":
                messages.append(encode_cc(122, value_int))
            elif key == "level" or key == "value":
                messages.append(encode_cc(123, value_int))
            elif key == "action" or key == "type":
                messages.append(encode_cc(124, value_int))
            elif key == "instrument" or key == "name":
                messages.append(encode_cc(125, value_int))
    
    # Command end marker (CC 126 with value 127)
    messages.append(encode_cc(126, 127))
    
    return messages

# For creating MIDI clips, we'll use a different approach - sending actual notes
def encode_midi_clip(notes, clear=True):
    """
    Encode a MIDI clip by sending the actual note events directly.
    This will be more reliable than trying to encode complex data structures.
    """
    messages = []
    
    # Send a command to clear existing notes if requested
    if clear:
        messages.extend(encode_command(1, {"clear": 1}))
        time.sleep(0.05)  # Small delay for FL Studio to process
    
    # Now send the actual note events
    for note_data in notes:
        note = note_data.get("note", 60)
        velocity = note_data.get("velocity", 100)
        # We'll ignore position and length for now, since those aren't working properly
        
        # Send note on (direct note event)
        messages.append(encode_note_on(note, velocity))
        
        # For chord progressions, space the notes slightly
        time.sleep(0.01)
    
    return messages

# Helper function to send a sequence of MIDI messages
def send_messages(messages):
    if output_port is None:
        logger.error("Cannot send MIDI messages: No output port available")
        return False
    
    try:
        for message in messages:
            logger.info(f"Sending MIDI message: {message}")
            output_port.send(message)
            # Small delay to avoid overloading the MIDI buffer
            time.sleep(0.005)
        return True
    except Exception as e:
        logger.error(f"Error sending MIDI messages: {e}")
        return False

# Define MCP tools
@mcp.tool()
def get_midi_ports() -> List[str]:
    """
    Get available MIDI output ports.
    
    Returns:
        A list of available MIDI output ports on the system.
    """
    try:
        ports = mido.get_output_names()
        logger.info(f"Available MIDI ports: {ports}")
        return ports
    except Exception as e:
        logger.error(f"Error getting MIDI ports: {e}")
        return []

@mcp.tool()
def play_note(note: int, velocity: int = 100, duration: float = 0.5) -> Dict[str, Any]:
    """
    Play a single note.
    
    Args:
        note: MIDI note number (0-127)
        velocity: Note velocity (0-127)
        duration: Note duration in seconds
    
    Returns:
        Status information about the played note.
    """
    if not 0 <= note <= 127:
        return {"error": "Note must be between 0 and 127"}
    
    if not 0 <= velocity <= 127:
        return {"error": "Velocity must be between 0 and 127"}
    
    logger.info(f"Playing note: {note}, velocity: {velocity}, duration: {duration}")
    
    # Send note on
    send_messages([encode_note_on(note, velocity)])
    
    # Schedule note off after duration
    time.sleep(duration)
    send_messages([encode_note_off(note)])
    
    return {"status": "success", "note": note, "velocity": velocity, "duration": duration}

@mcp.tool()
def create_midi_clip(notes: List[Dict[str, Any]], pattern: int = None, channel: int = None) -> Dict[str, Any]:
    """
    Create a MIDI clip with multiple notes.
    
    Args:
        notes: List of note dictionaries, each with:
            - note: MIDI note number (0-127)
            - velocity: Note velocity (0-127)
        pattern: Pattern number to use (optional)
        channel: Channel to use (optional)
    
    Returns:
        Status information about the created clip.
    """
    logger.info(f"Creating MIDI clip with {len(notes)} notes")
    
    # First send pattern selection if specified
    if pattern is not None:
        select_pattern(pattern)
        time.sleep(0.1)  # Give FL Studio time to process
    
    # Then send channel selection if specified
    if channel is not None:
        # Send a CC message to select the channel (CC 0 is commonly used for this)
        send_messages([encode_cc(0, min(127, channel))])
        time.sleep(0.1)  # Give FL Studio time to process
    
    # Now send the note events
    messages = encode_midi_clip(notes)
    success = send_messages(messages)
    
    if success:
        return {"status": "success", "notes_count": len(notes)}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def create_track(name: str, track_type: str = "instrument") -> Dict[str, Any]:
    """
    Create a new track in FL Studio.
    
    Args:
        name: Name for the track
        track_type: Type of track ("instrument", "audio", "automation")
    
    Returns:
        Status information about the created track.
    """
    logger.info(f"Creating new track: {name}, type: {track_type}")
    
    # Simplify track type to a numeric value
    type_value = 0  # Default instrument
    if track_type == "audio":
        type_value = 1
    elif track_type == "automation":
        type_value = 2
    
    # Create command for track creation
    command = encode_command(2, {"type": type_value, "name": name[0] if name else "T"})
    success = send_messages(command)
    
    # FL Studio needs some time to create the track
    time.sleep(0.5)
    
    if success:
        return {"status": "success", "track_type": track_type, "name": name}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def load_instrument(instrument_name: str, channel: int = None) -> Dict[str, Any]:
    """
    Load an instrument into a channel.
    
    Args:
        instrument_name: Name of the instrument to load (e.g., "piano", "bass", "drums")
        channel: Channel to load the instrument into (optional)
    
    Returns:
        Status information about the loaded instrument.
    """
    logger.info(f"Loading instrument: {instrument_name}")
    
    # Simplify instrument mapping to numeric values
    instrument_value = 0  # Default 
    
    if "piano" in instrument_name.lower():
        instrument_value = 1
    elif "bass" in instrument_name.lower():
        instrument_value = 2
    elif "drum" in instrument_name.lower():
        instrument_value = 3
    elif "synth" in instrument_name.lower():
        instrument_value = 4
    
    # First select channel if specified
    if channel is not None:
        # Send a CC message to select the channel (CC 0 is commonly used for this)
        send_messages([encode_cc(0, min(127, channel))])
        time.sleep(0.1)  # Give FL Studio time to process
    
    # Then send instrument load command
    command = encode_command(3, {"instrument": instrument_value})
    success = send_messages(command)
    
    # FL Studio needs some time to load the instrument
    time.sleep(0.5)
    
    if success:
        return {"status": "success", "instrument": instrument_name}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def set_tempo(bpm: int) -> Dict[str, Any]:
    """
    Set the project tempo.
    
    Args:
        bpm: Beats per minute (tempo)
    
    Returns:
        Status information about the tempo change.
    """
    logger.info(f"Setting tempo to {bpm} BPM")
    
    # Convert BPM to MIDI-compatible range (0-127)
    bpm_adjusted = min(127, max(0, bpm - 50))  # Assuming 50-177 BPM range
    
    # FL Studio often uses CC 16 for tempo control
    simple_message = [encode_cc(16, bpm_adjusted)]
    command = encode_command(4, {"bpm": bpm_adjusted})
    
    # Try both methods: direct CC and our encoded command protocol
    success = send_messages(simple_message)
    time.sleep(0.1)
    success = success and send_messages(command)
    
    if success:
        return {"status": "success", "bpm": bpm}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def control_transport(action: str = "toggle") -> Dict[str, Any]:
    """
    Control the transport (play, stop, record).
    
    Args:
        action: One of "play", "stop", "record", or "toggle"
    
    Returns:
        Status information about the transport action.
    """
    logger.info(f"Transport control: {action}")
    
    # FL Studio often uses standard MMC (MIDI Machine Control) messages
    # But we'll use both our command protocol and direct CC for compatibility
    
    action_value = 0  # Default to play
    if action == "stop":
        action_value = 1
    elif action == "record":
        action_value = 2
    elif action == "toggle":
        action_value = 3
    
    # Try using transport-specific MIDI CCs
    if action == "play" or action == "toggle":
        simple_message = [encode_cc(118, 127)]  # Common MIDI CC for start
    elif action == "stop":
        simple_message = [encode_cc(119, 127)]  # Common MIDI CC for stop
    elif action == "record":
        simple_message = [encode_cc(117, 127)]  # Common MIDI CC for record
    
    # Send both the simple message and our encoded command
    success = send_messages(simple_message)
    time.sleep(0.05)
    
    command = encode_command(5, {"action": action_value})
    success = success and send_messages(command)
    
    if success:
        return {"status": "success", "action": action}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def select_pattern(pattern: int) -> Dict[str, Any]:
    """
    Select a pattern by number.
    
    Args:
        pattern: Pattern number to select
    
    Returns:
        Status information about the pattern selection.
    """
    logger.info(f"Selecting pattern {pattern}")
    
    # FL Studio often uses Program Change for pattern selection
    # But we'll use both direct CC and our command protocol
    
    pattern_adjusted = min(127, max(0, pattern))
    
    # Try program change message (common for pattern selection)
    program_message = [mido.Message('program_change', program=pattern_adjusted)]
    success = send_messages(program_message)
    time.sleep(0.05)
    
    # Also send our encoded command
    command = encode_command(6, {"pattern": pattern_adjusted})
    success = success and send_messages(command)
    
    if success:
        return {"status": "success", "pattern": pattern}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def set_mixer_level(track: int = 0, level: float = 0.78) -> Dict[str, Any]:
    """
    Set mixer track volume level.
    
    Args:
        track: Mixer track (0 is master)
        level: Volume level (0.0 to 1.0)
    
    Returns:
        Status information about the mixer level change.
    """
    logger.info(f"Setting mixer track {track} level to {level}")
    
    # Convert level to MIDI range (0-127)
    level_adjusted = int(level * 127)
    
    # FL Studio often uses CCs in range 11-19 for mixer levels
    # Let's use a common approach plus our command
    
    # Each mixer track often has a dedicated CC
    mixer_cc = 11 + min(8, track)  # CCs 11-19 for tracks 0-8
    simple_message = [encode_cc(mixer_cc, level_adjusted)]
    success = send_messages(simple_message)
    time.sleep(0.05)
    
    # Also send our encoded command
    command = encode_command(7, {"track": track, "level": level})
    success = success and send_messages(command)
    
    if success:
        return {"status": "success", "track": track, "level": level}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def create_chord_progression(
    progression: List[str], 
    octave: int = 4, 
    pattern: Optional[int] = None,
    channel: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a chord progression using common chord names.
    
    Args:
        progression: List of chord names (e.g., ["C", "G", "Am", "F"])
        octave: Base octave for the chords
        pattern: Pattern number to create in (optional)
        channel: Channel to create in (optional)
    
    Returns:
        Status information about the created chord progression.
    """
    logger.info(f"Creating chord progression: {progression}, octave: {octave}")
    
    # Define chord note offsets
    chord_types = {
        "": [0, 4, 7],           # Major
        "m": [0, 3, 7],          # Minor
        "7": [0, 4, 7, 10],      # Dominant 7th
        "maj7": [0, 4, 7, 11],   # Major 7th
        "m7": [0, 3, 7, 10],     # Minor 7th
        "dim": [0, 3, 6],        # Diminished
        "aug": [0, 4, 8],        # Augmented
        "sus4": [0, 5, 7],       # Suspended 4th
        "sus2": [0, 2, 7],       # Suspended 2nd
    }
    
    # Define note values for each root
    root_notes = {
        "C": 60, "C#": 61, "Db": 61, "D": 62, "D#": 63, "Eb": 63,
        "E": 64, "F": 65, "F#": 66, "Gb": 66, "G": 67, "G#": 68,
        "Ab": 68, "A": 69, "A#": 70, "Bb": 70, "B": 71
    }
    
    # First select the pattern if specified
    if pattern is not None:
        select_pattern(pattern)
        time.sleep(0.1)
    
    # Then select the channel if specified
    if channel is not None:
        send_messages([encode_cc(0, min(127, channel))])
        time.sleep(0.1)
    
    # For FL Studio, we'll simplify by just sending the notes directly
    # This is more reliable than trying to encode complex chord data
    notes = []
    
    for i, chord_name in enumerate(progression):
        # Parse chord name (e.g., "Am7" -> root="A", type="m7")
        root = ""
        chord_type = ""
        
        for j, char in enumerate(chord_name):
            if j > 0 and (char.isdigit() or char in ['m', 'd', 'a', 's']):
                chord_type = chord_name[j:]
                break
            root += char
        
        # Get chord structure
        if chord_type in chord_types:
            offsets = chord_types[chord_type]
        else:
            # Handle complex chords by defaulting to major
            offsets = chord_types[""]
        
        # Get root note value
        if root in root_notes:
            root_value = root_notes[root] + (octave - 4) * 12
        else:
            # Default to C if invalid root
            root_value = 60 + (octave - 4) * 12
        
        # Create notes for this chord
        for offset in offsets:
            notes.append({
                "note": root_value + offset,
                "velocity": 90
            })
    
    # Send all notes - we'll simplify by just playing them
    messages = encode_midi_clip(notes)
    success = send_messages(messages)
    
    if success:
        return {"status": "success", "chords": len(progression)}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def fl_studio_direct_command(command_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Send a direct command to FL Studio.
    This is a flexible function for advanced users who understand FL Studio's MIDI mapping.
    
    Args:
        command_name: Name of the command (check FL documentation for supported commands)
        params: Dictionary of parameters for the command
    
    Returns:
        Status information about the command execution.
    """
    logger.info(f"Sending direct command: {command_name} with params: {params}")
    
    # Map common command names to MIDI CC values
    command_map = {
        "undo": [encode_cc(101, 127)],
        "redo": [encode_cc(102, 127)],
        "save": [encode_cc(103, 127)],
        "quantize": [encode_cc(104, 127)],
        "metronome": [encode_cc(105, 127)],
        "patterns_window": [encode_cc(106, 127)],
        "mixer_window": [encode_cc(107, 127)],
        "piano_roll": [encode_cc(108, 127)],
        "playlist": [encode_cc(109, 127)],
        "browser": [encode_cc(110, 127)],
    }
    
    if command_name.lower() in command_map:
        messages = command_map[command_name.lower()]
        success = send_messages(messages)
        
        if success:
            return {"status": "success", "command": command_name}
        else:
            return {"status": "error", "message": "Failed to send MIDI messages"}
    else:
        return {"status": "error", "message": f"Unknown command: {command_name}"}

# Run the MCP server
def main():
    logger.info("FL Studio MCP Server starting...")
    mcp.run()

if __name__ == "__main__":
    main()