import mido
import json
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("flstudio-mcp")

# Configure MIDI port
output_port = mido.open_output('IAC Driver MCP Bridge')

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
        
        # Send parameter length (CC 121)
        messages.append(encode_cc(121, len(param_bytes) & 127))
        messages.append(encode_cc(122, (len(param_bytes) >> 7) & 127))
        
        # Send parameter bytes (each byte split into two messages)
        for i, byte in enumerate(param_bytes):
            # Low 7 bits (CC 123)
            messages.append(encode_cc(123, byte & 127))
            # High 1 bit (CC 124)
            messages.append(encode_cc(124, (byte >> 7) & 1))
    
    return messages

# Helper function to send a sequence of MIDI messages
def send_messages(messages):
    for message in messages:
        output_port.send(message)

# Define MCP tools
@mcp.tool()
def get_midi_ports() -> List[str]:
    """Get available MIDI output ports."""
    return mido.get_output_names()

@mcp.tool()
def play_note(note: int, velocity: int = 100, duration: float = 0.5) -> Dict[str, Any]:
    """
    Play a single note.
    
    Args:
        note: MIDI note number (0-127)
        velocity: Note velocity (0-127)
        duration: Note duration in seconds
    """
    if not 0 <= note <= 127:
        return {"error": "Note must be between 0 and 127"}
    
    if not 0 <= velocity <= 127:
        return {"error": "Velocity must be between 0 and 127"}
    
    # Send note on
    send_messages([encode_note_on(note, velocity)])
    
    # Schedule note off after duration
    import time
    time.sleep(duration)
    send_messages([encode_note_off(note)])
    
    return {"status": "success", "note": note, "velocity": velocity, "duration": duration}

@mcp.tool()
def create_midi_clip(notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a MIDI clip with multiple notes.
    
    Args:
        notes: List of note dictionaries, each with:
            - note: MIDI note number (0-127)
            - velocity: Note velocity (0-100)
            - length: Note length in beats (decimal)
            - position: Note position in beats (decimal)
    """
    # Encode the create clip command
    command = encode_command(1, {"notes": notes})
    send_messages(command)
    
    return {"status": "success", "notes_count": len(notes)}

@mcp.tool()
def create_track(track_type: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new track in FL Studio.
    
    Args:
        track_type: Type of track ("audio", "midi", "instrument")
        name: Optional name for the track
    """
    # Encode the create track command
    command = encode_command(2, {"type": track_type, "name": name})
    send_messages(command)
    
    return {"status": "success", "track_type": track_type, "name": name}

@mcp.tool()
def load_instrument(instrument_name: str) -> Dict[str, Any]:
    """
    Load an instrument into the selected channel.
    
    Args:
        instrument_name: Name of the instrument to load
    """
    # Encode the load instrument command
    command = encode_command(3, {"instrument": instrument_name})
    send_messages(command)
    
    return {"status": "success", "instrument": instrument_name}

@mcp.tool()
def set_tempo(bpm: int) -> Dict[str, Any]:
    """
    Set the project tempo.
    
    Args:
        bpm: Beats per minute (tempo)
    """
    # Encode the set tempo command
    command = encode_command(4, {"bpm": bpm})
    send_messages(command)
    
    return {"status": "success", "bpm": bpm}

# Example tool: Get FL Studio version
@mcp.tool()
def get_fl_studio_version() -> str:
    """Get the version of FL Studio."""

# Run the MCP server
if __name__ == "__main__":
    print("FL Studio MCP Server starting...")
    mcp.run()

def main():
    print("FL Studio MCP Server starting...")
    mcp.run()
