"""
Channel-related commands and operations for FL Studio MCP Controller
"""

import channels
import time
import random
import math

# test / not sure if working
def cmd_create_notes(params, log_func, state):
    """Create or clear notes in the selected channel"""
    try:
        # Get parameters
        channel = params.get("track", channels.selectedChannel())
        clear = params.get("action", 0) > 0

        # Make sure we're working with a valid channel
        if channel >= channels.channelCount():
            return {"error": f"Invalid channel: {channel}"}

        # Select the channel
        channels.selectOneChannel(channel)
        state["selected_channel"] = channel

        # Clear notes if requested
        if clear:
            # Note: FL Studio doesn't have a direct API to clear notes
            # We would need more complex handling here
            log_func(f"Clearing notes on channel {channel} (not fully implemented)")
            # Consider adding MIDI events to delete existing notes

        return {"success": True, "channel": channel}
    except Exception as e:
        log_func(f"Error in create_notes: {str(e)}")
        return {"error": str(e)}

# test / not sure if working
def cmd_create_chord_progression(params, log_func):
    """Create a chord progression in the selected channel"""
    # This would need a complex implementation to translate chord types to actual notes
    # and create proper MIDI data in FL Studio
    log_func("Chord progression command received - requires direct note events")
    return {"success": False, "message": "Chord progressions require direct note events"}

# --- Channel Selection and Management ---

# working
def getCurrentChannelIndex(canBeNone=False):
    """Gets the index of the first selected channel in the current group.
    
    Args:
        canBeNone (bool): If True, returns -1 if no channel is selected. 
                        Otherwise, returns 0 (the first channel overall).
                        
    Returns:
        int: Index of the first selected channel (group-relative).
    """
    return channels.selectedChannel(canBeNone=canBeNone, offset=0, indexGlobal=False)



# not working
def getAllSelectedChannelIndices():
    """Gets a list of indices for all selected channels in the current group.
    
    Returns:
        list[int]: A list of group-relative indices.
    """
    selected_indices = []
    count = channels.channelCount(False) 
    for i in range(count):
        if channels.isChannelSelected(i, useGlobalIndex=False):
            selected_indices.append(i)
    return selected_indices

# working channel_commands.getChannelCount()
def getChannelCount():
    """Gets the number of channels in the current group."""
    return channels.channelCount()

# working channel_commands.getChannelCount()
def getGlobalChannelCount():
    """Gets the total number of channels across all groups."""
    return channels.channelCount(True)
    
# working channel_commands.isChannelSelected()
def isChannelSelected(index):
    """Checks if the channel at the group index is selected."""
    return channels.isChannelSelected(index, useGlobalIndex=False)

# working channel_commands.selectChannel()
def selectChannel(index):
    """Selects the channel at the group index (adds to current selection)."""
    channels.selectChannel(index, value=1, useGlobalIndex=False)
    
def selectChannels(indexStart, indexEnd):
    """Selects a range of channels in the current group."""
    for i in range(indexStart, indexEnd):
        channels.selectChannel(i, value=1, useGlobalIndex=False)

def deselectChannel(index):
    """Deselects the channel at the group index."""
    channels.selectChannel(index, value=0, useGlobalIndex=False)
    
def deselectChannels(indexStart, indexEnd):
    """Deselects a range of channels in the current group."""
    for i in range(indexStart, indexEnd):
        channels.selectChannel(i, value=0, useGlobalIndex=False)

def toggleChannelSelection(index):
    """Toggles the selection state of the channel at the group index."""
    channels.selectChannel(index, value=-1, useGlobalIndex=False)
    
def toggleChannelsSelection(indexStart, indexEnd):
    """Toggles the selection state of a range of channels in the current group."""
    for i in range(indexStart, indexEnd):
        channels.selectChannel(i, value=-1, useGlobalIndex=False)

def selectSingleChannel(index):
    """Selects *only* the channel at the group index, deselecting others."""
    channels.selectOneChannel(index, useGlobalIndex=False)

def selectAllChannels():
    """Selects all channels in the current group."""
    channels.selectAll() # Already simple and group-aware

def deselectAllChannels():
    """Deselects all channels in the current group."""
    channels.deselectAll() # Already simple and group-aware

# --- Channel Properties (Name, Color) ---

def get_channel_name(index):
    """Gets the name of the channel at the group index."""
    return channels.getChannelName(index, useGlobalIndex=False)

def get_channel_names():
    """Gets the names of all channels in the current group."""
    names = []
    for i in range(getChannelCount()):
        names.append(get_channel_name(i))
    return names

def setChannelName(index, name):
    """Sets the name of the channel at the group index."""
    channels.setChannelName(index, name, useGlobalIndex=False)

def getSelectedChannelName():
    """Gets the name of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        return get_channel_name(idx)
    return "" # Or raise error, depending on desired behavior

def setSelectedChannelName(name):
    """Sets the name of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        setChannelName(idx, name)
        
def getChannelColor(index):
    """Gets the color of the channel at the group index (0xBBGGRR)."""
    return channels.getChannelColor(index, useGlobalIndex=False)

def setChannelColor(index, color):
    """Sets the color of the channel at the group index (0xBBGGRR)."""
    channels.setChannelColor(index, color, useGlobalIndex=False)

def getSelectedChannelColor():
    """Gets the color of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        return getChannelColor(idx)
    return 0 # Or default color

def setSelectedChannelColor(color):
    """Sets the color of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        setChannelColor(idx, color)

def setSelectedChannelsColor(color):
    """Sets the color for ALL currently selected channels in the group."""
    selected_indices = getAllSelectedChannelIndices()
    for index in selected_indices:
        setChannelColor(index, color)

# --- Channel State (Mute, Solo) ---

def isChannelMuted(index):
    """Checks if the channel at the group index is muted."""
    return channels.isChannelMuted(index, False)

def toggleChannelMute(index):
    """Toggles the mute state of the channel at the group index."""
    channels.muteChannel(index, value=-1, useGlobalIndex=False)

def setChannelMute(index, muted):
    """Sets the mute state of the channel at the group index."""
    channels.muteChannel(index, value=1 if muted else 0, useGlobalIndex=False)

def toggleSelectedChannelMute():
    """Toggles the mute state of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        toggleChannelMute(idx)

def setSelectedChannelMute(muted):
    """Sets the mute state of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        setChannelMute(idx, muted)

def isChannelSolo(index):
    """Checks if the channel at the group index is soloed."""
    return channels.isChannelSolo(index, useGlobalIndex=False)

def toggleChannelSolo(index):
    """Toggles the solo state of the channel at the group index."""
    channels.soloChannel(index, useGlobalIndex=False) # Already toggles

def toggleSelectedChannelSolo():
    """Toggles the solo state of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        toggleChannelSolo(idx)

# --- Channel Audio Properties (Volume, Pan, Pitch) ---

def getChannelVolume(index):
    """Gets the normalized volume (0.0 to 1.0) of the channel at the group index."""
    return channels.getChannelVolume(index, mode=False, useGlobalIndex=False)

def setChannelVolume(index, volume):
    """Sets the normalized volume (0.0 to 1.0) of the channel at the group index."""
    import midi
    # Clamping volume to valid range
    volume = max(0.0, min(1.0, volume)) 
    channels.setChannelVolume(index, volume, pickupMode=midi.PIM_None, useGlobalIndex=False)

def getSelectedChannelVolume():
    """Gets the normalized volume of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        return getChannelVolume(idx)
    return 0.0 # Default or error

def setSelectedChannelVolume(volume):
    """Sets the normalized volume of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        setChannelVolume(idx, volume)
        
def getChannelPan(index):
    """Gets the normalized pan (-1.0 left to 1.0 right) of the channel at the group index."""
    return channels.getChannelPan(index, useGlobalIndex=False)

def setChannelPan(index, pan):
    """Sets the normalized pan (-1.0 left to 1.0 right) of the channel at the group index."""
    import midi
    # Clamping pan to valid range
    pan = max(-1.0, min(1.0, pan))
    channels.setChannelPan(index, pan, pickupMode=midi.PIM_None, useGlobalIndex=False)

def getSelectedChannelPan():
    """Gets the normalized pan of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        return getChannelPan(idx)
    return 0.0 # Default center pan

def setSelectedChannelPan(pan):
    """Sets the normalized pan of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        setChannelPan(idx, pan)

def getChannelPitch(index, mode=0):
    """Gets the pitch/range of the channel at the group index."""
    return channels.getChannelPitch(index, mode=0, useGlobalIndex=False)

def setChannelPitch(index, value, mode=0):
    """Sets the pitch/range of the channel at the group index."""
    import midi
    channels.setChannelPitch(index, value, mode=mode, pickupMode=midi.PIM_None, useGlobalIndex=False)

# --- Other Channel Info ---

def getChannelType(index):
    """Gets the type of the channel instrument at the group index."""
    return channels.getChannelType(index, useGlobalIndex=False)
    
def getSelectedChannelType():
    """Gets the type of the first selected channel."""
    idx = getCurrentChannelIndex()
    if idx >= 0:
        return getChannelType(idx)
    return -1 # Or appropriate "unknown" value

def getChannelMidiInPort(index):
    """Gets the MIDI input port for the channel at the group index."""
    return channels.getChannelMidiInPort(index, useGlobalIndex=False)

def getGlobalIndex(groupIndex):
    """Converts a group-relative index to a global index."""
    return channels.getChannelIndex(groupIndex) # Already does this conversion

def getTargetMixerTrack(channelIndex):
    """Gets the mixer track linked to the channel at the group index."""
    return channels.getTargetFxTrack(channelIndex, useGlobalIndex=False)

def setTargetMixerTrack(channelIndex, mixerIndex):
    """Sets the mixer track linked to the channel at the group index."""
    channels.setTargetFxTrack(channelIndex, mixerIndex, useGlobalIndex=False)
    
def getRecEventId(index):
    """Gets the REC event ID offset for the channel at the group index."""
    return channels.getRecEventId(index, useGlobalIndex=False)

def setSelectedChannelsPan(pan):
    """Set pan for all selected channels."""
    for index in getAllSelectedChannelIndices():
        setChannelPan(index, pan) 