# FL Studio MCP Controller Script
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

class TFLStudioMCPController:
    def __init__(self):
        print("FL Studio MCP Controller initialized")
        self.command_buffer = []
        self.param_buffer = bytearray()
        self.param_length = 0
        self.receiving_params = False
        self.current_command = None

    def OnMidiMsg(self, event):
        """Handle incoming MIDI messages"""
        if event.midiId == midi.MIDI_CONTROLCHANGE:
            # Command message handling
            if event.controller == 120:
                # Command type indicator
                self.current_command = event.controlVal
                self.command_buffer = []
                self.param_buffer = bytearray()
                self.param_length = 0
                self.receiving_params = True
            elif event.controller == 121 and self.receiving_params:
                # Parameter length (low 7 bits)
                self.param_length = event.controlVal
            elif event.controller == 122 and self.receiving_params:
                # Parameter length (high 7 bits)
                self.param_length |= (event.controlVal << 7)
                # Initialize parameter buffer
                self.param_buffer = bytearray()
            elif event.controller == 123 and self.receiving_params:
                # Parameter byte (low 7 bits)
                self.command_buffer.append(event.controlVal)
            elif event.controller == 124 and self.receiving_params:
                # Parameter byte (high 1 bit)
                if len(self.command_buffer) > 0:
                    byte = self.command_buffer.pop() | (event.controlVal << 7)
                    self.param_buffer.append(byte)
                    
                    # If we've received all parameter bytes, process the command
                    if len(self.param_buffer) >= self.param_length:
                        self.process_command()
                        self.receiving_params = False
        
        # Handle note events directly
        elif event.midiId == midi.MIDI_NOTEON:
            # Process direct note input
            channels.midiNoteOn(channels.selectedChannel(), event.note, event.velocity)
        elif event.midiId == midi.MIDI_NOTEOFF:
            # Process note off
            channels.midiNoteOn(channels.selectedChannel(), event.note, 0)

    def process_command(self):
        """Process a complete command with its parameters"""
        try:
            import json
            params = json.loads(self.param_buffer.decode('utf-8'))
            
            # Handle different command types
            if self.current_command == 1:  # Create MIDI clip
                self.create_midi_clip(params)
            elif self.current_command == 2:  # Create track
                self.create_track(params)
            elif self.current_command == 3:  # Load instrument
                self.load_instrument(params)
            elif self.current_command == 4:  # Set tempo
                self.set_tempo(params)
                
        except Exception as e:
            print(f"Error processing command: {e}")

    def create_midi_clip(self, params):
        """Create a MIDI clip with multiple notes"""
        notes = params.get("notes", [])
        
        # Get the selected pattern
        pattern = patterns.patternNumber()
        
        # Create notes in the selected channel
        channel = channels.selectedChannel()
        
        # First, clear any existing notes
        channels.clearNotes(channel)
        
        # Add all notes
        for note_data in notes:
            note = note_data.get("note", 60)
            velocity = note_data.get("velocity", 100)
            length = note_data.get("length", 1)
            position = note_data.get("position", 0)
            
            # Convert length and position from beats to ticks
            length_ticks = int(length * 960)  # 960 ticks per beat (quarter note)
            position_ticks = int(position * 960)
            
            # Add the note
            channels.addNote(
                channel,      # Channel index
                note,         # Note number
                velocity,     # Velocity
                position_ticks,  # Position in ticks
                length_ticks,    # Length in ticks
                False         # Don't select the note
            )

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

    def load_instrument(self, params):
        """Load an instrument into the selected channel"""
        instrument_name = params.get("instrument", "")
        
        # Get selected channel
        channel = channels.selectedChannel()
        
        # We would need to map instrument names to plugin indices
        # This is a simplified example - in a real implementation,
        # you would need to map instrument names to actual plugins
        if "piano" in instrument_name.lower():
            plugins.setParam(plugins.find("FL Keys", plugins.GENERATOR), 0, 0)  # Piano preset
        elif "bass" in instrument_name.lower():
            plugins.setParam(plugins.find("FLEX", plugins.GENERATOR), 0, 0)  # Bass preset
        # Add more instrument mappings as needed

    def set_tempo(self, params):
        """Set the project tempo"""
        bpm = params.get("bpm", 120)
        mixer.setMasterTempo(bpm)

def OnInit():
    """Called when the script is initialized"""
    global FlMCPController
    FlMCPController = TFLStudioMCPController()
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
