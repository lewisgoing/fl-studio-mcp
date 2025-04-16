"""
Transport-related commands and operations for FL Studio MCP Controller
"""

import transport
import patterns
import mixer
import general
import midi

def get_current_tempo():
    """Get the current project tempo in BPM"""
    try:
        tempo = mixer.getCurrentTempo() / 1000
        return tempo
    except Exception as e:
        print(f"Error getting tempo, using default: {e}")
        return 120  # Default fallback

def set_tempo(bpm):
    """Change the tempo in FL Studio to the specified BPM value
    
    Args:
        bpm: Can be a direct value or a params dictionary from MIDI
        
    Returns:
        dict: Status result
    """
    # Handle both direct BPM value and params dictionary
    if isinstance(bpm, dict):
        # This is a params dictionary from MIDI
        bpm_value = bpm.get("pattern", 70) + 50  # Convert from MIDI range
    else:
        # This is a direct BPM value
        bpm_value = bpm
    
    # Ensure BPM is in a reasonable range
    bpm_value = max(20, min(999, bpm_value))
    
    # FL Studio stores tempo as BPM * 1000
    tempo_value = int(bpm_value * 1000)
    
    # Use processRECEvent to set the tempo
    general.processRECEvent(
        midi.REC_Tempo,
        tempo_value,
        midi.REC_Control | midi.REC_UpdateControl
    )
    
    # Return success
    return {"success": True, "bpm": bpm_value}

def set_main_volume(volume):
    """Set the main volume in FL Studio
    
    Args:
        volume (float, int, or dict): Volume level can be:
                            - Float between 0.0 (0%) and 1.25 (125%)
                            - Integer between 0 and 125 (representing percentage)
                            - A params dictionary with 'value' key
    """
    try:
        # Handle both direct volume value and params dictionary
        if isinstance(volume, dict):
            # Convert from MIDI range (0-127) to 0-125% range
            volume_value = volume.get("value", 0) / 102.4  # 127/1.25 ≈ 102.4
        else:
            # Convert to float
            volume_value = float(volume)
            
            # If value is likely a percentage (greater than 1.25),
            # convert it to decimal format (e.g., 25 -> 0.25)
            if volume_value > 1.25:
                volume_value = volume_value / 100.0
        
        # Ensure volume is in valid range 0.0-1.25 (0-125%)
        volume_value = max(0.0, min(1.25, volume_value))
        
        # FL Studio seems to use a range that doesn't map linearly
        # For 0-125%, the effective range appears to be 0x0000-0xFFFF (0-65535)
        # But main volume uses a specific scale
        
        # Map 0.0-1.25 to 0-16384 (FL Studio's apparent scaling)
        # Adjust scaling factor to compensate for observed 2% error
        internal_value = int(volume_value * 12845.1)  # Adjusted from 13107.2 (reduced by ~2%)
        
        # Use processRECEvent to set the main volume
        general.processRECEvent(
            midi.REC_MainVol,
            internal_value,
            midi.REC_Control | midi.REC_UpdateValue | midi.REC_UpdateControl | midi.REC_ShowHint
        )
        
        return {"success": True, "volume": volume_value, "percent": int(volume_value * 100)}
    except Exception as e:
        print(f"Error setting main volume: {str(e)}")
        return {"error": str(e)}

def get_main_volume():
    """Get the current main volume level in FL Studio
    
    Returns:
        float: Current main volume as normalized value (0.0-1.25, representing 0-125%)
    """
    try:
        # Get the current main volume value
        internal_value = general.processRECEvent(
            midi.REC_MainVol,
            0,  # Value isn't used when just getting
            midi.REC_GetValue
        )
        
        # Convert from internal value to 0.0-1.25 range
        if internal_value < 0:
            return 0.0
            
        # Reverse the mapping: internal → 0.0-1.25
        normalized_value = internal_value / 13107.2
        
        return normalized_value
    except Exception as e:
        print(f"Error getting main volume: {str(e)}")
        return 0.0  # Default fallback

def cmd_transport_control(params):
    """Control transport (play, stop, record)"""
    try:
        # Get parameters
        action = params.get("action", 0) # 0=play, 1=stop, 2=record, 3=toggle

        if action == 0: # Play
            transport.start()
            return {"success": True, "action": "play"}
        elif action == 1: # Stop
            transport.stop()
            return {"success": True, "action": "stop"}
        elif action == 2: # Record
            transport.record()
            return {"success": True, "action": "record"}
        elif action == 3: # Toggle
            if transport.isPlaying():
                transport.stop()
                return {"success": True, "action": "stop"}
            else:
                transport.start()
                return {"success": True, "action": "play"}
        else:
            return {"error": f"Invalid transport action: {action}"}
    except Exception as e:
        print(f"Error in transport_control: {str(e)}")
        return {"error": str(e)}

def cmd_select_pattern(params):
    """Select a pattern in the playlist"""
    try:
        # Get parameters
        pattern = params.get("pattern", 0)

        # Check if pattern exists or create it
        if pattern >= patterns.patternCount():
            # Create new patterns up to the requested one
            current_count = patterns.patternCount()
            for i in range(current_count, pattern + 1):
                patterns.setPatternName(i, f"Pattern {i+1}")

        # Jump to the pattern
        patterns.jumpToPattern(pattern)
        return {"success": True, "pattern": pattern}
    except Exception as e:
        print(f"Error in select_pattern: {str(e)}")
        return {"error": str(e)} 