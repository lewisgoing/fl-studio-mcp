# name=FL Studio MCP Controller (Enhanced)
# url=https://github.com/lewisgoing/fl-studio-mcp

"""
Enhanced FL Studio MCP Integration Controller
"""

import midi
import channels
import patterns
import transport
import mixer
import plugins
import ui
import device
import general
import time
import json

# Constants
DEBUG = True
COMMAND_TIMEOUT = 5000  # ms

class MCPController:
    def __init__(self):
        self.command_buffer = []
        self.current_command = None
        self.command_complete = True
        self.last_command_time = 0
        self.response_data = {}
        self.log("FL Studio MCP Controller initialized")
        
        # Store state information
        self.state = {
            "selected_channel": 0,
            "selected_pattern": 0,
            "selected_mixer_track": 0,
            "last_created_channel": -1,
            "plugin_windows_open": []
        }
        
        # Print available ports for debugging
        self.print_ports()
    
    def log(self, message):
        if DEBUG:
            print(f"[MCP] {message}")
    
    def print_ports(self):
        try:
            self.log(f"Port number: {device.getPortNumber()}")
            self.log(f"Device name: {device.getName()}")
        except:
            self.log("Could not get device information")
    
    def send_feedback(self, data):
        """Send feedback to the server via MIDI SysEx"""
        try:
            if device.isAssigned():
                # Convert data to a simple string and send as SysEx
                message = json.dumps(data)[:100]  # Limit length for safety
                encoded = [ord(c) for c in message]
                # Create SysEx message with header F0 00 01 (custom header) and end with F7
                sysex_data = bytearray([0xF0, 0x00, 0x01] + encoded + [0xF7])
                device.midiOutSysex(bytes(sysex_data))
                self.log(f"Sent feedback: {message}")
        except Exception as e:
            self.log(f"Error sending feedback: {str(e)}")
    
    def OnMidiMsg(self, event):
        # Log incoming MIDI message if in debug mode
        if DEBUG:
            self.log(f"MIDI: id={event.midiId}, data1={event.data1}, data2={event.data2}")
        
        # Handle regular note input directly
        if event.midiId == midi.MIDI_NOTEON:
            if event.data2 > 0:  # Note on with velocity > 0
                index = channels.selectedChannel()
                channels.midiNoteOn(index, event.data1, event.data2)
                self.log(f"Playing note {event.data1} with velocity {event.data2} on channel {index}")
                return True
            else:  # Note on with velocity 0 is a note off
                channels.midiNoteOn(channels.selectedChannel(), event.data1, 0)
                return True
        
        elif event.midiId == midi.MIDI_NOTEOFF:
            channels.midiNoteOn(channels.selectedChannel(), event.data1, 0)
            return True
        
        # Handle command protocol messages
        elif event.midiId == midi.MIDI_CONTROLCHANGE:
            # Check for command start marker (CC 120)
            if event.data1 == 120:
                # Start a new command
                self.last_command_time = general.getTime()
                self.current_command = {
                    "type": event.data2,
                    "params": {}
                }
                self.command_complete = False
                self.log(f"Command start: type={event.data2}")
                return True
            
            # Check for parameters (CC 121-125)
            elif 121 <= event.data1 <= 125 and not self.command_complete:
                param_index = event.data1 - 121
                param_names = ["track", "pattern", "value", "action", "instrument"]
                if param_index < len(param_names):
                    param_name = param_names[param_index]
                    self.current_command["params"][param_name] = event.data2
                    self.log(f"Command param: {param_name}={event.data2}")
                return True
            
            # Check for command end marker (CC 126)
            elif event.data1 == 126 and not self.command_complete:
                self.command_complete = True
                self.log(f"Command complete: {self.current_command}")
                
                # Process the command immediately
                try:
                    result = self.process_command(self.current_command)
                    # Send feedback if available
                    if result:
                        self.send_feedback({"status": "success", "result": result})
                except Exception as e:
                    self.log(f"Error processing command: {str(e)}")
                    self.send_feedback({"status": "error", "message": str(e)})
                
                return True
            
            # Handle direct transport controls
            elif event.data1 == 118 and event.data2 > 0:  # Play
                transport.start()
                return True
            elif event.data1 == 119 and event.data2 > 0:  # Stop
                transport.stop()
                return True
            elif event.data1 == 117 and event.data2 > 0:  # Record
                transport.record()
                return True
        
        # Pass through other MIDI events
        return False
    
    def process_command(self, command):
        """Process a command received via MIDI"""
        cmd_type = command["type"]
        params = command["params"]
        
        # Store the last command for debugging
        self.log(f"Processing command type {cmd_type} with params {params}")
        
        if cmd_type == 1:    # Create or clear notes
            return self.cmd_create_notes(params)
        elif cmd_type == 2:  # Create track
            return self.cmd_create_track(params)
        elif cmd_type == 3:  # Load instrument
            return self.cmd_load_instrument(params)
        elif cmd_type == 4:  # Set tempo
            return self.cmd_set_tempo(params)
        elif cmd_type == 5:  # Transport control
            return self.cmd_transport_control(params)
        elif cmd_type == 6:  # Select pattern
            return self.cmd_select_pattern(params)
        elif cmd_type == 7:  # Set mixer level
            return self.cmd_set_mixer_level(params)
        elif cmd_type == 8:  # Create chord progression
            return self.cmd_create_chord_progression(params)
        elif cmd_type == 9:  # Add MIDI effect
            return self.cmd_add_midi_effect(params)
        elif cmd_type == 10: # Add audio effect
            return self.cmd_add_audio_effect(params)
        else:
            self.log(f"Unknown command type: {cmd_type}")
            return {"error": f"Unknown command type: {cmd_type}"}
    
    # Command implementations
    def cmd_create_notes(self, params):
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
            self.state["selected_channel"] = channel
            
            # Clear notes if requested
            if clear:
                # Note: FL Studio doesn't have a direct API to clear notes
                # We would need more complex handling here
                self.log(f"Clearing notes on channel {channel} (not fully implemented)")
                # Consider adding MIDI events to delete existing notes
            
            return {"success": True, "channel": channel}
        except Exception as e:
            self.log(f"Error in create_notes: {str(e)}")
            return {"error": str(e)}
    
    def cmd_create_track(self, params):
        """Create a new track in FL Studio"""
        try:
            # Get parameters
            track_type = params.get("action", 0)  # 0=instrument, 1=audio, 2=automation
            
            # FL Studio's channel creation process
            channel_index = channels.channelCount()
            if channel_index >= 125:  # FL Studio's limit
                return {"error": "Maximum number of channels reached"}
            
            # Add a channel to the channel rack
            channels.addChannel(track_type == 1)  # True for audio channel
            
            # Set the name based on type
            name = "Audio" if track_type == 1 else "Automation" if track_type == 2 else "Instrument"
            channels.setChannelName(channel_index, f"{name} {channel_index}")
            
            # Select the new channel
            channels.selectOneChannel(channel_index)
            self.state["selected_channel"] = channel_index
            self.state["last_created_channel"] = channel_index
            
            # Create a matching mixer track and link
            mixer_index = mixer.trackCount() - 1  # Leave master track alone
            if mixer_index < 125:
                mixer.setTrackName(mixer_index, f"{name} {channel_index}")
                # Link the channel to this mixer track
                channels.setTargetFxTrack(channel_index, mixer_index)
            
            self.log(f"Created new {name} track - channel: {channel_index}, mixer: {mixer_index}")
            return {"success": True, "channel": channel_index, "mixer": mixer_index, "type": name}
        except Exception as e:
            self.log(f"Error in create_track: {str(e)}")
            return {"error": str(e)}
    
    def cmd_load_instrument(self, params):
        """Load an instrument into a channel"""
        try:
            # Get parameters
            instrument_type = params.get("instrument", 0)
            channel = params.get("track", self.state["selected_channel"])
            
            # Make sure we're working with a valid channel
            if channel >= channels.channelCount():
                return {"error": f"Invalid channel: {channel}"}
            
            # Select the channel
            channels.selectOneChannel(channel)
            self.state["selected_channel"] = channel
            
            # Map instrument type to FL Studio plugin
            instrument_map = {
                1: "FL Keys",     # Piano
                2: "FLEX",        # Bass
                3: "FPC",         # Drums
                4: "3x Osc",      # Synth
                0: "Sampler"      # Default
            }
            
            # Get the instrument name
            instrument_name = instrument_map.get(instrument_type, "3x Osc")
            
            # Find the plugin index
            plugin_index = plugins.find(instrument_name)
            if plugin_index == -1:
                self.log(f"Plugin {instrument_name} not found")
                return {"error": f"Plugin {instrument_name} not found"}
            
            # Remove existing plugin if any
            if channels.getChannelType(channel) == channels.CT_GenPlug:
                # A generator plugin is already assigned
                pass  # We'll replace it
            
            # Load the instrument
            plugins.replace(channel, plugin_index)
            
            # For FLEX, try to set a preset based on type
            if instrument_name == "FLEX" and instrument_type == 2:  # Bass
                # Wait for the plugin to load
                time.sleep(0.5)
                # Try to find and set a bass preset
                # This requires more complex handling of plugin parameters
                
            self.log(f"Loaded {instrument_name} on channel {channel}")
            return {"success": True, "channel": channel, "instrument": instrument_name}
        except Exception as e:
            self.log(f"Error in load_instrument: {str(e)}")
            return {"error": str(e)}
    
    def cmd_set_tempo(self, params):
        """Set project tempo"""
        try:
            # Get parameters
            bpm = params.get("pattern", 0)
            
            # Convert from MIDI range back to actual BPM
            if 0 <= bpm <= 127:
                actual_bpm = bpm + 50  # 50-177 BPM range
                transport.setMainBPM(actual_bpm)
                self.log(f"Set tempo to {actual_bpm} BPM")
                return {"success": True, "bpm": actual_bpm}
            else:
                return {"error": f"Invalid BPM value: {bpm}"}
        except Exception as e:
            self.log(f"Error in set_tempo: {str(e)}")
            return {"error": str(e)}
    
    def cmd_transport_control(self, params):
        """Control transport (play, stop, record)"""
        try:
            # Get parameters
            action = params.get("action", 0)  # 0=play, 1=stop, 2=record, 3=toggle
            
            if action == 0:      # Play
                transport.start()
                self.log("Transport: Play")
                return {"success": True, "action": "play"}
            elif action == 1:    # Stop
                transport.stop()
                self.log("Transport: Stop")
                return {"success": True, "action": "stop"}
            elif action == 2:    # Record
                transport.record()
                self.log("Transport: Record")
                return {"success": True, "action": "record"}
            elif action == 3:    # Toggle
                if transport.isPlaying():
                    transport.stop()
                    self.log("Transport: Toggle -> Stop")
                    return {"success": True, "action": "stop"}
                else:
                    transport.start()
                    self.log("Transport: Toggle -> Play")
                    return {"success": True, "action": "play"}
            else:
                return {"error": f"Invalid transport action: {action}"}
        except Exception as e:
            self.log(f"Error in transport_control: {str(e)}")
            return {"error": str(e)}
    
    def cmd_select_pattern(self, params):
        """Select a pattern"""
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
            self.state["selected_pattern"] = pattern
            
            self.log(f"Selected pattern {pattern}")
            return {"success": True, "pattern": pattern}
        except Exception as e:
            self.log(f"Error in select_pattern: {str(e)}")
            return {"error": str(e)}
    
    def cmd_set_mixer_level(self, params):
        """Set mixer track volume level"""
        try:
            # Get parameters
            track = params.get("track", 0)
            level = params.get("value", 100) / 127.0  # Convert to 0.0-1.0
            
            # Ensure track exists
            if track >= mixer.trackCount():
                return {"error": f"Invalid mixer track: {track}"}
            
            # Set the volume
            mixer.setTrackVolume(track, level)
            self.log(f"Set mixer track {track} volume to {level}")
            
            return {"success": True, "track": track, "level": level}
        except Exception as e:
            self.log(f"Error in set_mixer_level: {str(e)}")
            return {"error": str(e)}
    
    def cmd_create_chord_progression(self, params):
        """Create a chord progression (placeholder - needs complex implementation)"""
        # This would need a complex implementation to translate chord types to actual notes
        # and create proper MIDI data in FL Studio
        self.log("Chord progression command received - requires direct note events")
        return {"success": False, "message": "Chord progressions require direct note events"}
    
    def cmd_add_midi_effect(self, params):
        """Add a MIDI effect to a channel"""
        # Implementation would depend on available MIDI effects
        self.log("Add MIDI effect command received")
        return {"success": False, "message": "MIDI effect addition not yet implemented"}
    
    def cmd_add_audio_effect(self, params):
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
                return {"error": f"Plugin {effect_name} not found"}
            
            # Add the effect
            mixer.trackPluginLoad(track, plugin_index, slot)
            self.log(f"Added {effect_name} to mixer track {track}, slot {slot}")
            
            return {"success": True, "track": track, "effect": effect_name, "slot": slot}
        except Exception as e:
            self.log(f"Error in add_audio_effect: {str(e)}")
            return {"error": str(e)}

    def OnIdle(self):
        """Called periodically"""
        # Check for command timeout
        if not self.command_complete and self.current_command is not None:
            current_time = general.getTime()
            if current_time - self.last_command_time > COMMAND_TIMEOUT:
                self.log(f"Command timeout: {self.current_command}")
                self.command_complete = True
                self.current_command = None

# Global instance
flMCPController = None

def OnInit():
    global flMCPController
    flMCPController = MCPController()
    return True

def OnDeInit():
    global flMCPController
    flMCPController = None
    return True

def OnMidiMsg(event):
    global flMCPController
    if flMCPController:
        return flMCPController.OnMidiMsg(event)
    return False

def OnIdle():
    global flMCPController
    if flMCPController:
        flMCPController.OnIdle()
    return True