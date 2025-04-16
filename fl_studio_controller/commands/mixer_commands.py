"""
Mixer-related commands and operations for FL Studio MCP Controller
"""

import mixer
import plugins

def cmd_set_mixer_level(params):
    """Set level for a mixer track"""
    try:
        # Get parameters
        track = params.get("track", 0)
        level = params.get("value", 100) / 127.0 # Convert to 0.0-1.0

        # Ensure track exists
        if track >= mixer.trackCount():
            return {"error": f"Invalid mixer track: {track}"}

        # Set the volume
        mixer.setTrackVolume(track, level)
        return {"success": True, "track": track, "level": level}
    except Exception as e:
        print(f"Error in set_mixer_level: {str(e)}")
        return {"error": str(e)}

def cmd_add_audio_effect(params):
    """Add an audio effect to a mixer track"""
    try:
        # Get parameters
        track = params.get("track", 0)
        effect_type = params.get("instrument", 0)

        # Map effect type to FL Studio plugin
        effect_map = {
            1: "Fruity Reverb 2",
            2: "Fruity Delay 3",
            3: "Fruity Parametric EQ 2",
            4: "Fruity Compressor",
            0: "Fruity Limiter"
        }

        # Get the effect name
        effect_name = effect_map.get(effect_type, "Fruity Limiter")

        # Find first empty slot
        slot = 0
        while slot < 10 and mixer.isTrackPluginValid(track, slot):
            slot += 1

        if slot >= 10:
            return {"error": "No empty effect slots available"}

        # Find the plugin index
        plugin_index = plugins.find(effect_name)  
        if plugin_index == -1:
            print(f"Effect '{effect_name}' not found.")
            # Try finding a default reverb or delay
            plugin_index = plugins.find("Fruity Reeverb 2")  
            if plugin_index == -1:
                plugin_index = plugins.find("Fruity Delay 3")  
                if plugin_index == -1:
                    return {"error": f"Could not find effect '{effect_name}' or default effects"}
            effect_name = plugins.getPluginName(plugin_index)

        # Add the effect to the first available slot
        slot_index = -1
        for i in range(10): # Max 10 slots
            if mixer.getTrackPluginId(track, i) == 0:
                slot_index = i
                break
        
        if slot_index == -1:
            return {"error": "No free effect slots on this track"}

        mixer.trackPluginLoad(track, slot_index, plugin_index)  

        return {"success": True, "track": track, "effect": effect_name, "slot": slot_index}
    except Exception as e:
        print(f"Error in add_audio_effect: {str(e)}")
        return {"error": str(e)} 