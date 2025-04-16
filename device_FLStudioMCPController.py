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
import random
import math
import arrangement

# Import command modules
from fl_studio_controller.commands import channel_commands
from fl_studio_controller.commands import transport_commands
from fl_studio_controller.commands import mixer_commands
from fl_studio_controller.commands import visual_commands

# Import testing module
from fl_studio_controller.testing.test_suite import TestSuite

# Constants
DEBUG = True
COMMAND_TIMEOUT = 5000 # ms

# Global animation state
animation_active = False
animation_frame = 0
animation_selected_only = False
animation_type = 0
animation_start_count = 0

# Step animation state
step_animation = {
    "current_frame": 0,
    "total_frames": 30,
    "animation_type": 0,
    "selected_only": False,
    "channels": []
}

# Smooth animation state (for auto-running animation)
smooth_animation = {
    "is_running": False,
    "start_time": 0,
    "frame_delay": 0.1,  # 100ms between frames
    "current_frame": 0,
    "total_frames": 30,
    "end_frame": 30,
    "animation_type": 0,
    "selected_only": False,
    "channels": []
}

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
                message = json.dumps(data)[:100] # Limit length for safety
                encoded = [ord(c) for c in message]
                # Create SysEx message with header F0 00 01 (custom header) and end with F7
                sysex_data = bytearray([0xF0, 0x00, 0x01] + encoded + [0xF7])
                device.midiOutSysex(bytes(sysex_data))
                self.log(f"Sent feedback: {message}")
        except Exception as e:
            self.log(f"Error sending feedback: {str(e)}")
    
    def update_animation_frame(self):
        """Update one frame of the color animation"""
        global animation_frame, animation_active, animation_type, animation_selected_only, animation_start_count
        
        try:
            if not animation_active:
                return
            
            # Get channel count
            total_channels = channels.channelCount()
            if total_channels == 0:
                return
            
            # Increment frame counter
            animation_frame += 1
            
            # Stop after ~60 seconds (at ~30fps this would be 1800 frames)
            if animation_start_count > 0 and animation_frame > 1800:
                self.log("Animation completed - maximum frames reached")
                animation_active = False
                return
                
            # Animation parameters
            frame_progress = (animation_frame % 120) / 120.0  # Cycle every 120 frames
            
            for i in range(total_channels):
                # Check if we should process this channel
                if animation_selected_only and not channels.isChannelSelected(i):
                    continue
                
                # Generate color based on animation type
                if animation_type == 0:  # Rainbow
                    # Rainbow gradient that shifts over time
                    hue = (i / total_channels + frame_progress) % 1.0
                    r, g, b = visual_commands.hsv_to_rgb(hue, 0.8, 0.9)
                    
                elif animation_type == 1:  # Pulse
                    # Pulsing intensity synchronized across channels
                    intensity = 0.5 + 0.5 * math.sin(frame_progress * 2 * math.pi)
                    base_hue = (i / total_channels) % 1.0  # Each channel has a fixed color
                    r, g, b = visual_commands.hsv_to_rgb(base_hue, 0.9, 0.4 + 0.6 * intensity)
                    
                else:  # Wave or other - default to wave pattern
                    # Wave pattern moving through channels
                    phase = (i / total_channels * 4 + frame_progress * 2) % 1.0
                    intensity = 0.5 + 0.5 * math.sin(phase * 2 * math.pi)
                    hue = (i / total_channels * 0.2 + frame_progress * 0.1) % 1.0
                    r, g, b = visual_commands.hsv_to_rgb(hue, 0.7 + 0.3 * intensity, 0.9)
                
                # Scale to 0-255 range
                r = int(r * 255)
                g = int(g * 255)
                b = int(b * 255)
                
                # Convert to FL Studio color format (0xBBGGRR)
                color = (b << 16) | (g << 8) | r
                
                # Set the channel color
                channels.setChannelColor(i, color)
            
        except Exception as e:
            self.log(f"Error updating animation: {str(e)}")
            animation_active = False

    def OnMidiMsg(self, event):
        # Log incoming MIDI message if in debug mode
        if DEBUG:
            self.log(f"MIDI: id={event.midiId}, data1={event.data1}, data2={event.data2}")

        # Handle regular note input directly
        if event.midiId == midi.MIDI_NOTEON:
            if event.data2 > 0: # Note on with velocity > 0
                index = channels.selectedChannel()
                channels.midiNoteOn(index, event.data1, event.data2)
                self.log(f"Playing note {event.data1} with velocity {event.data2} on channel {index}")
                return True
            else: # Note on with velocity 0 is a note off
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
                self.last_command_time = time.time() * 1000  # using time.time() instead of general.getTime()
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
                if param_index < len(param_names) and self.current_command is not None:
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
            elif event.data1 == 118 and event.data2 > 0: # Play
                transport.start()
                return True
            elif event.data1 == 119 and event.data2 > 0: # Stop
                transport.stop()
                return True
            elif event.data1 == 117 and event.data2 > 0: # Record
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

        # ===== CONTENT CREATION COMMANDS =====
        if cmd_type == 1: # Create or clear notes
            return channel_commands.cmd_create_notes(params, self.log, self.state)
        elif cmd_type == 8: # Create chord progression
            return channel_commands.cmd_create_chord_progression(params, self.log)
            
        # ===== TRACK AND CHANNEL MANAGEMENT COMMANDS =====
        elif cmd_type == 2: # Create track
            # Note: Not implemented yet
            return {"error": "Create track command not implemented"}
        elif cmd_type == 3: # Load instrument
            # Note: Not implemented yet
            return {"error": "Load instrument command not implemented"}
            
        # ===== TRANSPORT CONTROL COMMANDS =====
        elif cmd_type == 4: # Set tempo
            return transport_commands.set_tempo(params)
        elif cmd_type == 5: # Transport control (play, stop, record)
            return transport_commands.cmd_transport_control(params)
        elif cmd_type == 6: # Select pattern
            return transport_commands.cmd_select_pattern(params)
            
        # ===== MIXER OPERATION COMMANDS =====
        elif cmd_type == 7: # Set mixer level
            return mixer_commands.cmd_set_mixer_level(params)
            
        # ===== EFFECTS COMMANDS =====
        elif cmd_type == 9: # Add MIDI effect
            # Note: Not implemented yet
            return {"error": "Add MIDI effect command not implemented"}
        elif cmd_type == 10: # Add audio effect
            return mixer_commands.cmd_add_audio_effect(params)
            
        # ===== VISUAL/UI COMMANDS =====
        elif cmd_type == 11: # Randomize channel colors
            return visual_commands.cmd_randomize_colors(params)
        else:
            self.log(f"Unknown command type: {cmd_type}")
            return {"error": f"Unknown command type: {cmd_type}"}

    def OnIdle(self):
        """Called periodically"""
        # Check for command timeout
        if not self.command_complete and self.current_command is not None:
            current_time = time.time() * 1000  # using time.time() instead of general.getTime()
            if current_time - self.last_command_time > COMMAND_TIMEOUT:
                self.log(f"Command timeout: {self.current_command}")
                self.command_complete = True
                self.current_command = None
                
        # Update animation if active
        global animation_active
        if animation_active:
            self.update_animation_frame()

# Global instance
flMCPController = None

def OnInit():
    """Called when loaded by FL Studio"""
    global flMCPController
    flMCPController = MCPController()
    
    print("FL Studio MCP Controller initialized! Have fun!")
    print("type -h for help")
    
    return

def OnDeInit():
    """Called when the script is unloaded by FL Studio"""
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

def OnTransport(isPlaying):
    """Called when the transport state changes (play/stop)"""
    print(f"Transport state changed: {'Playing' if isPlaying else 'Stopped'}")
    return

def OnTempoChange(tempo):
    """Called when the tempo changes"""
    print(f"Tempo changed to: {tempo} BPM")
    return

# Direct utility functions that can be called from FL Studio scripts
def RandomizeAllChannelColors():
    """Utility function to randomize colors for all channels"""
    return visual_commands.randomize_channel_colors(False)

def RandomizeSelectedChannelColors():
    """Utility function to randomize colors for selected channels only"""
    return visual_commands.randomize_channel_colors(True)

def AnimationSetup(animation_type=0, selected_only=False, total_frames=30):
    """Set up a step-by-step animation that can be manually advanced"""
    return visual_commands.animation_setup(animation_type, selected_only, total_frames)

def NextAnimationFrame(animation_state):
    """Render the next frame of the step animation"""
    return visual_commands.next_animation_frame(animation_state)

def RunSmoothAnimation(animation_type=0, selected_only=False, duration_seconds=5, frames_per_second=10):
    """Start a smooth animation that runs for the specified duration"""
    result = visual_commands.run_smooth_animation(animation_type, selected_only, duration_seconds, frames_per_second)
    
    # In the real implementation, we would need to add a timer mechanism to 
    # call render_animation_frame repeatedly, but that's UI framework specific
    
    return result

def StopSmoothAnimation(animation_state):
    """Stop any running animation"""
    return visual_commands.stop_animation(animation_state)

# Preset effects
def RainbowPattern(selected_only=False):
    """Apply a rainbow pattern across channels"""
    return visual_commands.rainbow_pattern(selected_only)

def ColorGroups(selected_only=False, groups=4):
    """Color channels in distinct groups"""
    return visual_commands.color_groups(selected_only, groups)

def RandomColors(selected_only=False, brightness=0.9):
    """Apply random colors to channels"""
    return visual_commands.random_colors(selected_only, brightness)

def ColorByType(selected_only=False):
    """Color channels based on their type"""
    return visual_commands.color_by_type(selected_only)

def GradientPreset(preset=0, selected_only=False):
    """Apply a preset gradient to channels"""
    return visual_commands.gradient_preset(preset, selected_only)

def RunTests():
    """Run all tests in the test suite"""
    print("Starting FL Studio MCP Controller test suite...")
    test_suite = TestSuite(channel_commands)
    return test_suite.run_all_tests()