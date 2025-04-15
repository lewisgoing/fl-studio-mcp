# name=FL Studio MCP (User)
# url=https://github.com/lewisgoing/fl-studio-mcp (Optional: Add your repo link here)

"""
FL Studio MIDI Remote Script for MCP Integration.
This script runs inside FL Studio and listens for commands from the external MCP server via a socket.
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
import json

class FLStudioMCPController:
    def __init__(self):
        self.command_buffer = []
        self.param_buffer = bytearray()
        self.param_length = 0
        self.receiving_params = False
        self.current_command = None
        self.log("FL Studio MCP Controller initialized")
    
    def log(self, message):
        """Helper to log messages to FL Studio console"""
        print(f"[MCP] {message}")

    def OnMidiMsg(self, event):
        """Handle incoming MIDI messages"""
        # Log incoming MIDI message for debugging
        self.log(f"MIDI: id={event.midiId}, data1={event.data1}, data2={event.data2}")
        
        if event.midiId == midi.MIDI_CONTROLCHANGE:
            # Command message handling
            if event.data1 == 120:
                # Command type indicator
                self.current_command = event.data2
                self.log(f"Command start: {self.current_command}")
                self.command_buffer = []
                self.param_buffer = bytearray()
                self.param_length = 0
                self.receiving_params = True
            elif event.data1 == 121 and self.receiving_params:
                # Parameter length (low 7 bits)
                self.param_length = event.data2
            elif event.data1 == 122 and self.receiving_params:
                # Parameter length (high 7 bits)
                self.param_length |= (event.data2 << 7)
                self.log(f"Expecting {self.param_length} bytes of parameter data")
                # Initialize parameter buffer
                self.param_buffer = bytearray()
            elif event.data1 == 123 and self.receiving_params:
                # Parameter byte (low 7 bits)
                self.command_buffer.append(event.data2)
            elif event.data1 == 124 and self.receiving_params:
                # Parameter byte (high 1 bit)
                if len(self.command_buffer) > 0:
                    byte = self.command_buffer.pop() | (event.data2 << 7)
                    self.param_buffer.append(byte)
                    
                    # If we've received all parameter bytes, process the command
                    if len(self.param_buffer) == self.param_length:
                        self.log(f"Command complete, processing...")
                        self.process_command()
                        self.receiving_params = False
        
        # Handle note events directly
        elif event.midiId == midi.MIDI_NOTEON:
            # Process direct note input
            channels.midiNoteOn(channels.selectedChannel(), event.data1, event.data2)
        elif event.midiId == midi.MIDI_NOTEOFF:
            # Process note off
            channels.midiNoteOn(channels.selectedChannel(), event.data1, 0)

    def process_command(self):
        """Process a complete command with its parameters"""
        try:
            params_str = self.param_buffer.decode('utf-8')
            self.log(f"Received params: {params_str}")
            params = json.loads(params_str)
            
            # Handle different command types
            if self.current_command == 1:  # Create MIDI clip
                self.create_midi_clip(params)
            elif self.current_command == 2:  # Create track
                self.create_track(params)
            elif self.current_command == 3:  # Load instrument
                self.load_instrument(params)
            elif self.current_command == 4:  # Set tempo
                self.set_tempo(params)
            elif self.current_command == 5:  # Play/stop transport
                self.control_transport(params)
            elif self.current_command == 6:  # Select pattern
                self.select_pattern(params)
            elif self.current_command == 7:  # Set mixer level
                self.set_mixer_level(params)
            elif self.current_command == 8:  # Add automation
                self.add_automation(params)
            else:
                self.log(f"Unknown command type: {self.current_command}")
                
        except Exception as e:
            self.log(f"Error processing command: {e}")

    def create_midi_clip(self, params):
        """Create a MIDI clip with multiple notes"""
        notes = params.get("notes", [])
        pattern = params.get("pattern", patterns.patternNumber())
        channel = params.get("channel", channels.selectedChannel())
        
        # Select the pattern first
        patterns.jumpToPattern(pattern)
        
        # First, clear any existing notes if requested
        if params.get("clear", True):
            channels.clearNotes(channel)
        
        # Add all notes
        for note_data in notes:
            note = note_data.get("note", 60)
            velocity = note_data.get("velocity", 100)
            length = note_data.get("length", 1)
            position = note_data.get("position", 0)
            
            # Convert length and position from beats to ticks
            # FL Studio uses PPQ of 960 (pulses per quarter note)
            length_ticks = int(length * 960)
            position_ticks = int(position * 960)
            
            # Add the note
            channels.addNote(
                channel,         # Channel index
                note,            # Note number
                velocity,        # Velocity
                position_ticks,  # Position in ticks
                length_ticks,    # Length in ticks
                False            # Don't select the note
            )
        
        self.log(f"Created MIDI clip with {len(notes)} notes in pattern {pattern}, channel {channel}")

    def create_track(self, params):
        """Create a new track"""
        track_type = params.get("type", "instrument")
        track_name = params.get("name", "New Track")
        
        # Add a new channel
        channel_index = channels.channelCount()
        if channel_index < 100:  # FL Studio has a limit on channels
            channels.addChannel()
            channels.setChannelName(channel_index, track_name)
            
            # Select the new channel
            channels.selectOneChannel(channel_index)
            self.log(f"Created new {track_type} track: {track_name} (channel {channel_index})")
        else:
            self.log("Cannot create more channels: limit reached")

    def load_instrument(self, params):
        """Load an instrument into the selected channel"""
        instrument_name = params.get("instrument", "").lower()
        channel = params.get("channel", channels.selectedChannel())
        
        # Select the channel first
        channels.selectOneChannel(channel)
        
        # Map common instrument names to FL Studio plugins
        self.log(f"Trying to load instrument: {instrument_name}")
        
        if "piano" in instrument_name:
            plugins.instantiate(plugins.pluginIndex("FL Keys", plugins.GENERATOR))
            # For FL Keys, 0 = piano preset
            plugins.setPreset("Piano", 1)
            self.log("Loaded FL Keys (Piano)")
        elif "bass" in instrument_name:
            plugins.instantiate(plugins.pluginIndex("FLEX", plugins.GENERATOR))
            # Try to find a bass preset in FLEX
            plugins.setPreset("Bass", 1)
            self.log("Loaded FLEX (Bass)")
        elif "drum" in instrument_name or "kit" in instrument_name:
            plugins.instantiate(plugins.pluginIndex("FPC", plugins.GENERATOR))
            # Load default drum kit
            plugins.setPreset("Drums", 1)
            self.log("Loaded FPC (Drums)")
        elif "synth" in instrument_name:
            plugins.instantiate(plugins.pluginIndex("3x Osc", plugins.GENERATOR))
            self.log("Loaded 3x Osc (Synth)")
        else:
            # Default to 3x Osc if no specific match
            plugins.instantiate(plugins.pluginIndex("3x Osc", plugins.GENERATOR))
            self.log(f"No specific match for '{instrument_name}', loaded 3x Osc")

    def set_tempo(self, params):
        """Set the project tempo"""
        bpm = params.get("bpm", 120)
        mixer.setMasterTempo(bpm)
        self.log(f"Set tempo to {bpm} BPM")

    def control_transport(self, params):
        """Control the transport (play, stop, record)"""
        action = params.get("action", "toggle")
        
        if action == "play":
            transport.start()
            self.log("Started playback")
        elif action == "stop":
            transport.stop()
            self.log("Stopped playback")
        elif action == "record":
            transport.record()
            self.log("Started recording")
        elif action == "toggle":
            transport.start()
            self.log("Toggled playback")

    def select_pattern(self, params):
        """Select a pattern by number"""
        pattern_num = params.get("pattern", 0)
        patterns.jumpToPattern(pattern_num)
        self.log(f"Selected pattern {pattern_num}")

    def set_mixer_level(self, params):
        """Set mixer track volume level"""
        track = params.get("track", 0)  # 0 is master
        level = params.get("level", 0.78)  # Default is around -3dB
        
        # Scale level from 0-1 to FL Studio's internal range
        mixer.setTrackVolume(track, level)
        self.log(f"Set mixer track {track} level to {level}")

    def add_automation(self, params):
        """Add automation to a parameter"""
        plugin = params.get("plugin", -1)  # -1 means mixer
        param = params.get("param", 0)
        points = params.get("points", [])
        
        if plugin == -1:
            # Mixer automation
            track = params.get("track", 0)
            self.log(f"Adding mixer automation to track {track}, param {param}")
            
            for point in points:
                pos = point.get("position", 0) * 960  # Convert beats to ticks
                value = point.get("value", 0.5)
                # FL Studio API for adding automation points
                mixer.automateEvent(track, param, pos, value, 0)
        else:
            # Plugin parameter automation
            self.log(f"Adding plugin automation to plugin {plugin}, param {param}")
            # Implementation would depend on FL Studio's API for plugin automation

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