import mido
import time
import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('flstudio-mcp')

# Initialize MCP server
mcp: FastMCP = FastMCP("flstudio-mcp")

# MIDI port handling
output_port = None

try:
    available_ports = mido.get_output_names()
    logger.info(f"Available MIDI ports: {available_ports}")
    
    # Try to find IAC Driver port
    for port in available_ports:
        if 'IAC Driver MCP Bridge' in port:
            output_port = mido.open_output(port)
            logger.info(f"Connected to MIDI port: {port}")
            break
    
    # Fallback to any IAC port
    if output_port is None:
        for port in available_ports:
            if 'IAC' in port:
                output_port = mido.open_output(port)
                logger.info(f"Connected to MIDI port: {port}")
                break
    
    if output_port is None:
        logger.error("No IAC Driver port found. Please configure the IAC Driver.")
except Exception as e:
    logger.error(f"Error initializing MIDI: {e}")

# Enhanced command sending with better feedback
def send_command(command_type, params=None, wait_for_feedback=True):
    """
    Send a command to FL Studio with improved error handling and feedback
    """
    if output_port is None:
        logger.error("Cannot send command: No MIDI output port available")
        return {"status": "error", "message": "No MIDI output port available"}
    
    try:
        # Command start
        output_port.send(mido.Message('control_change', control=120, value=command_type))
        
        # Send parameters
        if params:
            for key, value in params.items():
                param_cc = None
                if key in ["track", "channel"]:
                    param_cc = 121
                elif key in ["pattern", "bpm"]:
                    param_cc = 122
                elif key in ["value", "level"]:
                    param_cc = 123
                elif key in ["action", "type"]:
                    param_cc = 124
                elif key in ["instrument", "name"]:
                    param_cc = 125
                
                if param_cc:
                    # Convert value to MIDI range
                    midi_value = 0
                    if isinstance(value, bool):
                        midi_value = 127 if value else 0
                    elif isinstance(value, float):
                        # Scale float between 0-1 to 0-127
                        if 0 <= value <= 1:
                            midi_value = int(value * 127)
                        else:
                            midi_value = min(127, max(0, int(value)))
                    elif isinstance(value, int):
                        midi_value = min(127, max(0, value))
                    
                    output_port.send(mido.Message('control_change', control=param_cc, value=midi_value))
                    time.sleep(0.01) # Small delay between parameters
        
        # Command end
        output_port.send(mido.Message('control_change', control=126, value=127))
        
        # TODO: Implement feedback listening mechanism if wait_for_feedback is True
        return {"status": "success", "command": command_type, "params": params}
    
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return {"status": "error", "message": str(e)}

# Enhanced MCP tool implementations
@mcp.tool()
def get_midi_ports() -> List[str]:
    """Get available MIDI output ports."""
    try:
        ports = mido.get_output_names()
        logger.info(f"Available MIDI ports: {ports}")
        return ports
    except Exception as e:
        logger.error(f"Error getting MIDI ports: {e}")
        return []

@mcp.tool()
def play_note(note: int, velocity: int = 100, duration: float = 0.5) -> Dict[str, Any]:
    """Play a single MIDI note."""
    if not 0 <= note <= 127:
        return {"status": "error", "message": "Note must be between 0 and 127"}
    if not 0 <= velocity <= 127:
        return {"status": "error", "message": "Velocity must be between 0 and 127"}
    
    try:
        # Send note on
        if output_port:
            output_port.send(mido.Message('note_on', note=note, velocity=velocity))
            time.sleep(duration)
            output_port.send(mido.Message('note_off', note=note, velocity=0))
            logger.info(f"Played note {note} with velocity {velocity} for {duration}s")
            return {"status": "success", "note": note, "velocity": velocity, "duration": duration}
        else:
            return {"status": "error", "message": "No MIDI output port available"}
    except Exception as e:
        logger.error(f"Error playing note: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def create_track(name: str = "New Track", track_type: str = "instrument") -> Dict[str, Any]:
    """Create a new track in FL Studio with proper instrument loading."""
    try:
        # Map track type to value
        type_value = 0 # Default (instrument)
        if track_type.lower() == "audio":
            type_value = 1
        elif track_type.lower() == "automation":
            type_value = 2
        
        # Send command to create track
        result = send_command(2, {"type": type_value})
        logger.info(f"Created track: {result}")
        return result
    except Exception as e:
        logger.error(f"Error creating track: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def load_instrument(instrument_name: str, channel: Optional[int] = None) -> Dict[str, Any]:
    """Load an instrument into the selected or specified channel."""
    try:
        # Map instrument name to type
        instrument_value = 0 # Default
        if "piano" in instrument_name.lower():
            instrument_value = 1
        elif "bass" in instrument_name.lower():
            instrument_value = 2
        elif "drum" in instrument_name.lower():
            instrument_value = 3
        elif "synth" in instrument_name.lower():
            instrument_value = 4
        
        params = {"instrument": instrument_value}
        if channel is not None:
            params["track"] = channel
        
        # Send command to load instrument
        result = send_command(3, params)
        logger.info(f"Loaded instrument: {result}")
        return result
    except Exception as e:
        logger.error(f"Error loading instrument: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def set_tempo(bpm: int) -> Dict[str, Any]:
    """Set the project tempo."""
    try:
        if not 50 <= bpm <= 999:
            return {"status": "error", "message": "BPM must be between 50 and 999"}
        
        # Convert to MIDI value range
        bpm_adjusted = min(127, max(0, bpm - 50)) # 50-177 BPM mapped to 0-127
        
        # Send command to set tempo
        result = send_command(4, {"pattern": bpm_adjusted})
        logger.info(f"Set tempo to {bpm} BPM")
        return result
    except Exception as e:
        logger.error(f"Error setting tempo: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def control_transport(action: str = "toggle") -> Dict[str, Any]:
    """Control transport (play, stop, record)."""
    try:
        # Map action to value
        action_value = 3 # Default (toggle)
        if action.lower() == "play":
            action_value = 0
        elif action.lower() == "stop":
            action_value = 1
        elif action.lower() == "record":
            action_value = 2
        
        # Try direct transport controls first (more reliable)
        if output_port:
            if action.lower() == "play":
                output_port.send(mido.Message('control_change', control=118, value=127))
            elif action.lower() == "stop":
                output_port.send(mido.Message('control_change', control=119, value=127))
            elif action.lower() == "record":
                output_port.send(mido.Message('control_change', control=117, value=127))
            time.sleep(0.05) # Small delay
        
        # Then send command for complex handling
        result = send_command(5, {"action": action_value})
        logger.info(f"Transport control: {action}")
        return result
    except Exception as e:
        logger.error(f"Error controlling transport: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def select_pattern(pattern: int) -> Dict[str, Any]:
    """Select a pattern by number."""
    try:
        if not 0 <= pattern <= 999:
            return {"status": "error", "message": "Pattern must be between 0 and 999"}
        
        pattern_adjusted = min(127, pattern) # Limit to MIDI range
        
        # Try program change for direct selection first
        if output_port:
            output_port.send(mido.Message('program_change', program=pattern_adjusted))
            time.sleep(0.05) # Small delay
        
        # Then send command for complex handling (creates pattern if needed)
        result = send_command(6, {"pattern": pattern_adjusted})
        logger.info(f"Selected pattern {pattern}")
        return result
    except Exception as e:
        logger.error(f"Error selecting pattern: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def set_mixer_level(track: int = 0, level: float = 0.78) -> Dict[str, Any]:
    """Set mixer track volume level."""
    try:
        if not 0 <= track <= 125:
            return {"status": "error", "message": "Track must be between 0 and 125"}
        if not 0 <= level <= 1:
            return {"status": "error", "message": "Level must be between 0.0 and 1.0"}
        
        # Try direct mixer control first
        if output_port and track <= 8:
            # CCs 11-19 often map to first 9 mixer tracks
            mixer_cc = 11 + track
            level_adjusted = int(level * 127)
            output_port.send(mido.Message('control_change', control=mixer_cc, value=level_adjusted))
            time.sleep(0.05) # Small delay
        
        # Send command for proper handling
        result = send_command(7, {"track": track, "value": int(level * 127)})
        logger.info(f"Set mixer track {track} level to {level}")
        return result
    except Exception as e:
        logger.error(f"Error setting mixer level: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def create_chord_progression(
    progression: List[str],
    octave: int = 4,
    pattern: Optional[int] = None
) -> Dict[str, Any]:
    """Create a chord progression using direct note events."""
    try:
        # First select pattern if specified
        if pattern is not None:
            select_pattern(pattern)
            time.sleep(0.1)
        
        # Define chord note offsets
        chord_types = {
            "": [0, 4, 7], # Major
            "m": [0, 3, 7], # Minor
            "7": [0, 4, 7, 10], # Dominant 7th
            "maj7": [0, 4, 7, 11], # Major 7th
            "m7": [0, 3, 7, 10], # Minor 7th
            "dim": [0, 3, 6], # Diminished
            "aug": [0, 4, 8], # Augmented
            "sus4": [0, 5, 7], # Suspended 4th
            "sus2": [0, 2, 7], # Suspended 2nd
        }
        
        # Define note values for each root
        root_notes = {
            "C": 60, "C#": 61, "Db": 61, "D": 62, "D#": 63, "Eb": 63,
            "E": 64, "F": 65, "F#": 66, "Gb": 66, "G": 67, "G#": 68,
            "Ab": 68, "A": 69, "A#": 70, "Bb": 70, "B": 71
        }
        
        # For each chord, play its notes as direct MIDI events
        for chord_name in progression:
            # Parse chord name
            root = ""
            chord_type = ""
            for j, char in enumerate(chord_name):
                if j > 0 and (char.isdigit() or char in ['m', 'd', 'a', 's']):
                    chord_type = chord_name[j:]
                    break
                root += char
            
            # Get chord structure
            offsets = chord_types.get(chord_type, chord_types[""])
            
            # Get root note value
            if root in root_notes:
                root_value = root_notes[root] + (octave - 4) * 12
            else:
                # Default to C if invalid root
                root_value = 60 + (octave - 4) * 12
            
            # Play notes for this chord
            if output_port:
                for offset in offsets:
                    note = root_value + offset
                    if 0 <= note <= 127:
                        output_port.send(mido.Message('note_on', note=note, velocity=90))
                        time.sleep(0.01) # Small delay between notes
                
                # Let chord play for a moment before next chord
                time.sleep(0.5)
                
                # Send note offs for all notes
                for offset in offsets:
                    note = root_value + offset
                    if 0 <= note <= 127:
                        output_port.send(mido.Message('note_off', note=note, velocity=0))
                time.sleep(0.1) # Gap between chords
        
        return {"status": "success", "progression": progression}
    except Exception as e:
        logger.error(f"Error creating chord progression: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
def add_audio_effect(track: int = 0, effect_type: str = "reverb") -> Dict[str, Any]:
    """Add an audio effect to a mixer track."""
    try:
        # Map effect type to value
        effect_value = 0 # Default (limiter)
        if "reverb" in effect_type.lower():
            effect_value = 1
        elif "delay" in effect_type.lower():
            effect_value = 2
        elif "eq" in effect_type.lower():
            effect_value = 3
        elif "comp" in effect_type.lower():
            effect_value = 4
        
        # Send command to add effect
        result = send_command(10, {"track": track, "instrument": effect_value})
        logger.info(f"Added {effect_type} effect to track {track}")
        return result
    except Exception as e:
        logger.error(f"Error adding audio effect: {e}")
        return {"status": "error", "message": str(e)}

def main():
    logger.info("Starting FL Studio MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
