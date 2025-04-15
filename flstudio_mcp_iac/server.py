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

# Define special command encoding
def encode_command(command_type, params=None):
    """
    Encode a command as a series of MIDI messages.
    Since MIDI messages are limited to 7-bit values (0-127),
    we need to encode complex data across multiple messages.
    """
    messages = []
    
    # Command type indicator (CC 120)
    messages.append(encode_cc(120, command_type))
    
    # If we have parameters, encode them
    if params:
        # Convert params to JSON and then to bytes
        param_bytes = json.dumps(params).encode('utf-8')
        
        # Send parameter length (CC 121 for low 7 bits, CC 122 for high 7 bits)
        messages.append(encode_cc(121, len(param_bytes) & 127))
        messages.append(encode_cc(122, (len(param_bytes) >> 7) & 127))
        
        # Send parameter bytes (each byte split into two messages)
        for byte in param_bytes:
            # Low 7 bits (CC 123)
            messages.append(encode_cc(123, byte & 127))
            # High 1 bit (CC 124)
            messages.append(encode_cc(124, (byte >> 7) & 1))
    
    return messages

# Helper function to send a sequence of MIDI messages
def send_messages(messages):
    if output_port is None:
        logger.error("Cannot send MIDI messages: No output port available")
        return False
    
    try:
        for message in messages:
            output_port.send(message)
            # Small delay to avoid overloading the MIDI buffer
            time.sleep(0.001)
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
def create_midi_clip(notes: List[Dict[str, Any]], pattern: int = None, channel: int = None, clear: bool = True) -> Dict[str, Any]:
    """
    Create a MIDI clip with multiple notes.
    
    Args:
        notes: List of note dictionaries, each with:
            - note: MIDI note number (0-127)
            - velocity: Note velocity (0-100)
            - length: Note length in beats (decimal)
            - position: Note position in beats (decimal)
        pattern: Pattern number to create notes in (optional)
        channel: Channel to create notes in (optional)
        clear: Whether to clear existing notes (default: True)
    
    Returns:
        Status information about the created clip.
    """
    logger.info(f"Creating MIDI clip with {len(notes)} notes")
    
    # Encode the create clip command
    params = {
        "notes": notes,
        "clear": clear
    }
    
    if pattern is not None:
        params["pattern"] = pattern
        
    if channel is not None:
        params["channel"] = channel
    
    command = encode_command(1, params)
    success = send_messages(command)
    
    if success:
        return {"status": "success", "notes_count": len(notes)}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def create_track(track_type: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new track in FL Studio.
    
    Args:
        track_type: Type of track ("audio", "midi", "instrument")
        name: Optional name for the track
    
    Returns:
        Status information about the created track.
    """
    logger.info(f"Creating new track: {name}, type: {track_type}")
    
    # Encode the create track command
    command = encode_command(2, {"type": track_type, "name": name})
    success = send_messages(command)
    
    if success:
        return {"status": "success", "track_type": track_type, "name": name}
    else:
        return {"status": "error", "message": "Failed to send MIDI messages"}

@mcp.tool()
def load_instrument(instrument_name: str, channel: Optional[int] = None) -> Dict[str, Any]:
    """
    Load an instrument into a channel.
    
    Args:
        instrument_name: Name of the instrument to load (e.g., "piano", "bass", "drums")
        channel: Channel to load the instrument into (optional, uses selected channel if omitted)
    
    Returns:
        Status information about the loaded instrument.
    """
    logger.info(f"Loading instrument: {instrument_name}")
    
    params = {"instrument": instrument_name}
    if channel is not None:
        params["channel"] = channel
        
    # Encode the load instrument command
    command = encode_command(3, params)
    success = send_messages(command)
    
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
    
    # Encode the set tempo command
    command = encode_command(4, {"bpm": bpm})
    success = send_messages(command)
    
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
    
    # Encode the transport command
    command = encode_command(5, {"action": action})
    success = send_messages(command)
    
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
    
    # Encode the select pattern command
    command = encode_command(6, {"pattern": pattern})
    success = send_messages(command)
    
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
    
    # Encode the mixer level command
    command = encode_command(7, {"track": track, "level": level})
    success = send_messages(command)
    
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
    
    notes = []
    for i, chord_name in enumerate(progression):
        # Parse chord name (e.g., "Am7" -> root="A", type="m7")
        root = ""
        for j, char in enumerate(chord_name):
            if j > 0 and (char.isdigit() or char in ['m', 'd', 'a', 's']):
                chord_type = chord_name[j:]
                break
            root += char
        else:
            chord_type = ""
        
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
        
        # Create notes for this chord (one bar per chord)
        for offset in offsets:
            notes.append({
                "note": root_value + offset,
                "velocity": 90,
                "length": 4.0,  # 4 beats = 1 bar
                "position": i * 4.0  # Position in beats
            })
    
    # Create the MIDI clip
    return create_midi_clip(notes, pattern, channel)

# Run the MCP server
def main():
    logger.info("FL Studio MCP Server starting...")
    mcp.run()

if __name__ == "__main__":
    main()