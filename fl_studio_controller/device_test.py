# name=FL Studio MCP Controller
# url=https://github.com/lewisgoing/fl-studio-mcp

"""
FL Studio MIDI Remote Script for MCP Integration.
This script runs inside FL Studio and listens for commands from the external MCP server via MIDI.
"""

import midi
import channels
import patterns
import transport
import arrangement
import plugins
import mixer
import ui
import device
import general

# Debug mode - set to True to enable verbose logging
DEBUG = True

class FLStudioMCPController:
    def __init__(self):
        self.current_command = None
        self.command_params = {}
        self.receiving_command = False
        self.log("FL Studio MCP Controller initialized")
        self.print_ports()
    
    def log(self, message):
        """Helper to log messages to FL Studio console"""
        if DEBUG:
            print(f"[MCP] {message}")
    
    def print_ports(self):
        """Print available MIDI ports for debugging"""
        try:
            self.log("Available input ports:")
            for i in range(device.midiInCount()):
                self.log(f"  {i}: {device.midiInGetName(i)}")
            
            self.log("Available output ports:")
            for i in range(device.midiOutCount()):
                self.log(f"  {i}: {device.midiOutGetName(i)}")
        except:
            self.log("Could not enumerate MIDI ports")

    def OnMidiMsg(self, event):
        """Handle incoming MIDI messages"""
        # Log incoming MIDI message for debugging
        if DEBUG:
            self.log(f"MIDI: id={event.midiId}, data1={event.data1}, data2={event.data2}")
        
        # Handle note events directly
        if event.midiId == midi.MIDI_NOTEON:
            if event.data2 > 0:  # Note on with velocity > 0
                channels.midiNoteOn(channels.selectedChannel(), event.data1, event.data2)
                if DEBUG:
                    self.log(f"Playing note {event.data1} with velocity {event.data2}")
            else:  # Note on with velocity 0 is effectively a note off
                channels.midiNoteOn(channels.selectedChannel(), event.data1, 0)
                if DEBUG:
                    self.log(f"Stopping note {event.data1}")
        
        elif event.midiId == midi.MIDI_NOTEOFF:
            channels.midiNoteOn(channels.selectedChannel(), event.data1, 0)
            if DEBUG:
                self.log(f"Note off: {event.data1}")
        
        # Handle control change messages
        elif event.midiId == midi.MIDI_CONTROLCHANGE:
            # Check for direct control messages first (common FL Studio MIDI mappings)
            if event.data1 == 16:  # Tempo control
                bpm = event.data2 + 50  # Assuming 50-177 BPM range
                self.log(f"Setting tempo (direct): {bpm} BPM")
                mixer.setMasterTempo(bpm)
            
            elif event.data1 >= 11 and event.data1 <= 19:  # Mixer levels
                track = event.data1 - 11
                level = event.data2 / 127
                self.log(f"Setting mixer level (direct): track {track}, level {level}")
                mixer.setTrackVolume(track, level)
            
            elif event.data1 == 0:  # Channel selection
                channel = event.data2
                self.log(f"Selecting channel (direct): {channel}")
                if channel < channels.channelCount():
                    channels.selectOneChannel(channel)
            
            # Handle the command protocol
            elif event.data1 == 120:  # Command start
                self.current_command = event.data2
                self.command_params = {}
                self.receiving_command = True
                self.log(f"Command start: {self.current_command}")
            
            elif event.data1 >= 121 and event.data1 <= 125 and self.receiving_command:
                # Parameter values
                param_name = {
                    121: "track/channel",
                    122: "pattern/bpm",
                    123: "level/value",
                    124: "action/type",
                    125: "instrument/name"
                }.get(event.data1)
                
                self.command_params[param_name] = event.data2
                self.log(f"Command param: {param_name} = {event.data2}")
            
            elif event.data1 == 126 and self.receiving_command:
                # Command end, process the command
                self.log(f"Command end, processing command: {self.current_command}")
                self.process_command()
                self.receiving_command = False
            
            # Handle common transport controls
            elif event.data1 == 118 and event.data2 > 0:  # Play
                self.log("Transport: Play (direct)")
                transport.start()
            
            elif event.data1 == 119 and event.data2 > 0:  # Stop
                self.log("Transport: Stop (direct)")
                transport.stop()
            
            elif event.data1 == 117 and event.data2 > 0:  # Record
                self.log("Transport: Record (direct)")
                transport.record()
            
            # Handle other direct commands
            elif event.data1 == 101 and event.data2 > 0:  # Undo
                self.log("Undo (direct)")
                general.undoUp()
            
            elif event.data1 == 102 and event.data2 > 0:  # Redo
                self.log("Redo (direct)")
                general.undoDown()
            
        # Handle program change (pattern selection)
        elif event.midiId == midi.MIDI_PROGRAMCHANGE:
            pattern = event.data1
            self.log(f"Selecting pattern (direct): {pattern}")
            if pattern < patterns.patternCount():
                patterns.jumpToPattern(pattern)

    def process_command(self):
        """Process a complete command with its parameters"""
        try:
            # Handle different command types
            if self.current_command == 1:  # Create MIDI clip / clear notes
                clear = self.command_params.get("action/type", 0) > 0
                channel = self.command_params.get("track/channel", channels.selectedChannel())
                
                if clear and channel < channels.channelCount():
                    self.log(f"Clearing notes on channel {channel}")
                    channels.clearNotes(channel)
            
            elif self.current_command == 2:  # Create track
                track_type = self.command_params.get("action/type", 0)
                self.log(f"Creating track, type: {track_type}")
                
                # Add a new channel
                channel_index = channels.channelCount()
                if channel_index < 100:  # FL Studio has a limit on channels
                    channels.addChannel()
                    
                    # Name it based on type
                    name = "Audio" if track_type == 1 else "Automation" if track_type == 2 else "Instrument"
                    channels.setChannelName(channel_index, name)
                    
                    # Select the new channel
                    channels.selectOneChannel(channel_index)
                    self.log(f"Created new track (channel {channel_index})")
            
            elif self.current_command == 3:  # Load instrument
                instrument_type = self.command_params.get("instrument/name", 0)
                channel = self.command_params.get("track/channel", channels.selectedChannel())
                
                # Select the channel
                if channel < channels.channelCount():
                    channels.selectOneChannel(channel)
                    
                    # Load instrument based on type
                    self.log(f"Loading instrument type: {instrument_type} to channel {channel}")
                    
                    if instrument_type == 1:  # Piano
                        if plugins.isValid(channels.selectedChannel()):
                            plugins.remove(channels.selectedChannel())
                        plugins.instantiate(plugins.find("FL Keys"))
                        self.log("Loaded FL Keys (Piano)")
                    
                    elif instrument_type == 2:  # Bass
                        if plugins.isValid(channels.selectedChannel()):
                            plugins.remove(channels.selectedChannel())
                        plugins.instantiate(plugins.find("FLEX"))
                        # Try to set a bass preset
                        gen = channels.getChannelGenerator(channels.selectedChannel())
                        if gen != -1:
                            plugins.setPresetName(gen, "Bass")
                        self.log("Loaded FLEX (Bass)")
                    
                    elif instrument_type == 3:  # Drums
                        if plugins.isValid(channels.selectedChannel()):
                            plugins.remove(channels.selectedChannel())
                        plugins.instantiate(plugins.find("FPC"))
                        self.log("Loaded FPC (Drums)")
                    
                    elif instrument_type == 4:  # Synth
                        if plugins.isValid(channels.selectedChannel()):
                            plugins.remove(channels.selectedChannel())
                        plugins.instantiate(plugins.find("3x Osc"))
                        self.log("Loaded 3x Osc (Synth)")
                    
                    else:
                        # Default
                        if plugins.isValid(channels.selectedChannel()):
                            plugins.remove(channels.selectedChannel())
                        plugins.instantiate(plugins.find("3x Osc"))
                        self.log("Loaded default instrument (3x Osc)")
            
            elif self.current_command == 4:  # Set tempo
                bpm = self.command_params.get("pattern/bpm", 0)
                
                if bpm > 0:
                    bpm = bpm + 50  # Scale back to reasonable BPM range (50-177)
                    self.log(f"Setting tempo: {bpm} BPM")
                    mixer.setMasterTempo(bpm)
            
            elif self.current_command == 5:  # Transport control
                action = self.command_params.get("action/type", 0)
                
                if action == 0:  # Play
                    self.log("Transport: Play")
                    transport.start()
                elif action == 1:  # Stop
                    self.log("Transport: Stop")
                    transport.stop()
                elif action == 2:  # Record
                    self.log("Transport: Record")
                    transport.record()
                elif action == 3:  # Toggle
                    self.log("Transport: Toggle")
                    if transport.isPlaying():
                        transport.stop()
                    else:
                        transport.start()
            
            elif self.current_command == 6:  # Select pattern
                pattern = self.command_params.get("pattern/bpm", 0)
                
                self.log(f"Selecting pattern: {pattern}")
                if pattern < patterns.patternCount():
                    patterns.jumpToPattern(pattern)
                else:
                    # Create new patterns up to the requested one
                    current_count = patterns.patternCount()
                    for i in range(current_count, pattern + 1):
                        patterns.setPatternName(i, f"Pattern {i}")
                    patterns.jumpToPattern(pattern)
            
            elif self.current_command == 7:  # Set mixer level
                track = self.command_params.get("track/channel", 0)
                level = self.command_params.get("level/value", 100) / 127.0
                
                self.log(f"Setting mixer level: track {track}, level {level}")
                if track < mixer.trackCount():
                    mixer.setTrackVolume(track, level)
            
            else:
                self.log(f"Unknown command type: {self.current_command}")
                
        except Exception as e:
            self.log(f"Error processing command: {str(e)}")

# Global FL Studio MCP controller instance
FlMCPController = None

def OnInit():
    """Called when the script is initialized"""
    global FlMCPController
    FlMCPController = FLStudioMCPController()
    return True

def OnDeInit():
    """Called when the script is deinitialized"""
    global FlMCPController
    FlMCPController = None
    return True

def OnMidiMsg(event):
    """MIDI message callback"""
    global FlMCPController
    if FlMCPController:
        FlMCPController.OnMidiMsg(event)
    return True

def OnIdle():
    """Called on idle"""
    return True

def OnRefresh():
    """Called when the script is refreshed"""
    return True