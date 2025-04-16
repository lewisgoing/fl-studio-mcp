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

    def randomize_channel_colors(self, selected_only=False):
        """Randomize the colors of all channels or just selected ones
        
        Args:
            selected_only (bool): If True, only randomize colors of selected channels
        
        Returns:
            dict: Result information
        """
        try:
            count = 0
            # Get the number of channels
            total_channels = channels.channelCount()
            
            for i in range(total_channels):
                # Check if we should process this channel
                if selected_only and not channels.isChannelSelected(i):
                    continue
                
                # Generate a random color in 0xBBGGRR format (FL Studio uses this format)
                # Each component is 0-255
                r = random.randint(30, 255)
                g = random.randint(30, 255)
                b = random.randint(30, 255)
                
                # Convert to FL Studio color format (0xBBGGRR)
                color = (b << 16) | (g << 8) | r
                
                # Set the channel color
                channels.setChannelColor(i, color)
                count += 1
            
            self.log(f"Randomized colors for {count} channels")
            return {"success": True, "count": count}
        except Exception as e:
            self.log(f"Error randomizing colors: {str(e)}")
            return {"error": str(e)}

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
                    r, g, b = self._hsv_to_rgb(hue, 0.8, 0.9)
                    
                elif animation_type == 1:  # Pulse
                    # Pulsing intensity synchronized across channels
                    intensity = 0.5 + 0.5 * math.sin(frame_progress * 2 * math.pi)
                    base_hue = (i / total_channels) % 1.0  # Each channel has a fixed color
                    r, g, b = self._hsv_to_rgb(base_hue, 0.9, 0.4 + 0.6 * intensity)
                    
                else:  # Wave or other - default to wave pattern
                    # Wave pattern moving through channels
                    phase = (i / total_channels * 4 + frame_progress * 2) % 1.0
                    intensity = 0.5 + 0.5 * math.sin(phase * 2 * math.pi)
                    hue = (i / total_channels * 0.2 + frame_progress * 0.1) % 1.0
                    r, g, b = self._hsv_to_rgb(hue, 0.7 + 0.3 * intensity, 0.9)
                
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
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB
        
        Args:
            h (float): Hue (0-1)
            s (float): Saturation (0-1)
            v (float): Value (0-1)
            
        Returns:
            tuple: RGB values as floats (0-1)
        """
        if s == 0.0:
            return v, v, v
            
        h *= 6
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        
        if i == 0:
            return v, t, p
        elif i == 1:
            return q, v, p
        elif i == 2:
            return p, v, t
        elif i == 3:
            return p, q, v
        elif i == 4:
            return t, p, v
        else:
            return v, p, q

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
            return self.cmd_create_notes(params)
        elif cmd_type == 8: # Create chord progression
            return self.cmd_create_chord_progression(params)
            
        # ===== TRACK AND CHANNEL MANAGEMENT COMMANDS =====
        elif cmd_type == 2: # Create track
            return self.cmd_create_track(params)
        elif cmd_type == 3: # Load instrument
            return self.cmd_load_instrument(params)
            
        # ===== TRANSPORT CONTROL COMMANDS =====
        elif cmd_type == 4: # Set tempo
            return self.set_tempo(params)  # Fix: Pass params instead of undefined bpm
        elif cmd_type == 5: # Transport control (play, stop, record)
            return self.cmd_transport_control(params)
        elif cmd_type == 6: # Select pattern
            return self.cmd_select_pattern(params)
            
        # ===== MIXER OPERATION COMMANDS =====
        elif cmd_type == 7: # Set mixer level
            return self.cmd_set_mixer_level(params)
            
        # ===== EFFECTS COMMANDS =====
        elif cmd_type == 9: # Add MIDI effect
            return self.cmd_add_midi_effect(params)
        elif cmd_type == 10: # Add audio effect
            return self.cmd_add_audio_effect(params)
            
        # ===== VISUAL/UI COMMANDS =====
        elif cmd_type == 11: # Randomize channel colors
            return self.cmd_randomize_colors(params)
        else:
            self.log(f"Unknown command type: {cmd_type}")
            return {"error": f"Unknown command type: {cmd_type}"}

    # ===== CONTENT CREATION COMMANDS =====
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

    def cmd_create_chord_progression(self, params):
        """Create a chord progression in the selected channel"""
        # This would need a complex implementation to translate chord types to actual notes
        # and create proper MIDI data in FL Studio
        self.log("Chord progression command received - requires direct note events")
        return {"success": False, "message": "Chord progressions require direct note events"}

    # ===== TRACK AND CHANNEL MANAGEMENT COMMANDS =====
    # add generator function: todo
    
    
    
    # ===== TRANSPORT/GLOBAL CONTROL COMMANDS =====
    def get_current_tempo(self):
        """Get the current project tempo in BPM"""
        try:
            tempo = mixer.getCurrentTempo() / 1000
            self.log(f"Current project tempo: {tempo} BPM")
            return tempo
        except Exception as e:
            self.log(f"Error getting tempo, using default: {e}")
            return 120  # Default fallback

    def set_tempo(self, bpm):
        """Change the tempo in FL Studio to the specified BPM value"""
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
        
        # Log the change
        self.log(f"Set tempo to {bpm_value} BPM")
        
        # Return success
        return {"success": True, "bpm": bpm_value}
    

    def set_main_volume(self, volume):
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
            
            print(f"Setting main volume to {volume_value}")
            
            # Map 0.0-1.25 to 0-16384 (FL Studio's apparent scaling)
            # Adjust scaling factor to compensate for observed 2% error
            internal_value = int(volume_value * 12845.1)  # Adjusted from 13107.2 (reduced by ~2%)
            
            print(f"Setting main volume to {internal_value}")
            
            # Use processRECEvent to set the main volume
            general.processRECEvent(
                midi.REC_MainVol,
                internal_value,
                midi.REC_Control | midi.REC_UpdateValue | midi.REC_UpdateControl | midi.REC_ShowHint
            )
            
            self.log(f"Set main volume to {volume_value:.2f} ({int(volume_value * 100)}%)")
            return {"success": True, "volume": volume_value, "percent": int(volume_value * 100)}
        except Exception as e:
            self.log(f"Error setting main volume: {str(e)}")
            return {"error": str(e)}
    
    def get_main_volume(self):
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
            
            # Format for display
            self.log(f"Current main volume: {normalized_value:.2f} ({int(normalized_value * 100)}%)")
            return normalized_value
        except Exception as e:
            self.log(f"Error getting main volume: {str(e)}")
            return 0.0  # Default fallback

    def cmd_transport_control(self, params):
        """Control transport (play, stop, record)"""
        try:
            # Get parameters
            action = params.get("action", 0) # 0=play, 1=stop, 2=record, 3=toggle

            if action == 0: # Play
                transport.start()
                self.log("Transport: Play")
                return {"success": True, "action": "play"}
            elif action == 1: # Stop
                transport.stop()
                self.log("Transport: Stop")
                return {"success": True, "action": "stop"}
            elif action == 2: # Record
                transport.record()
                self.log("Transport: Record")
                return {"success": True, "action": "record"}
            elif action == 3: # Toggle
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
            self.state["selected_pattern"] = pattern
            self.log(f"Selected pattern {pattern}")
            return {"success": True, "pattern": pattern}
        except Exception as e:
            self.log(f"Error in select_pattern: {str(e)}")
            return {"error": str(e)}


    # ===== MIXER OPERATION COMMANDS =====
    def cmd_set_mixer_level(self, params):
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
            self.log(f"Set mixer track {track} volume to {level}")
            return {"success": True, "track": track, "level": level}
        except Exception as e:
            self.log(f"Error in set_mixer_level: {str(e)}")
            return {"error": str(e)}

    # ===== EFFECTS COMMANDS =====

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
                self.log(f"Effect '{effect_name}' not found.")
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

            self.log(f"Added effect '{effect_name}' to mixer track {track}, slot {slot_index}")
            return {"success": True, "track": track, "effect": effect_name, "slot": slot_index}
        except Exception as e:
            self.log(f"Error in add_audio_effect: {str(e)}")
            return {"error": str(e)}

    # ===== VISUAL/UI COMMANDS =====
    def cmd_randomize_colors(self, params):
        """Randomize channel colors in the channel rack"""
        try:
            # Get parameters
            selected_only = params.get("value", 0) > 0
            
            # Call the randomize function
            result = self.randomize_channel_colors(selected_only)
            
            self.log(f"Randomized channel colors (selected only: {selected_only})")
            return result
        except Exception as e:
            self.log(f"Error in randomize_colors: {str(e)}")
            return {"error": str(e)}

    def OnIdle(self):
        """Called periodically"""
        # Check for command timeout
        if not self.command_complete and self.current_command is not None:
            current_time = 0  # Changed from general.getTime() which doesn't exist
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
    global flMCPController
    if flMCPController:
        return flMCPController.randomize_channel_colors(False)
    return {"error": "Controller not initialized"}

def RandomizeSelectedChannelColors():
    """Utility function to randomize colors for selected channels only"""
    global flMCPController
    if flMCPController:
        return flMCPController.randomize_channel_colors(True)
    return {"error": "Controller not initialized"}

def AnimationSetup(animation_type=0, selected_only=False, total_frames=30):
    """Set up a step-by-step animation that can be manually advanced
    
    Args:
        animation_type (int): 0=rainbow shift, 1=pulse, 2=color cycle
        selected_only (bool): Only animate selected channels
        total_frames (int): Total number of frames in the animation
    """
    global step_animation, flMCPController
    
    try:
        # Identify channels to animate
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        # Reset animation state
        step_animation = {
            "current_frame": 0,
            "total_frames": total_frames,
            "animation_type": animation_type,
            "selected_only": selected_only,
            "channels": channels_to_color
        }
        
        if flMCPController:
            flMCPController.log(f"Animation setup: type {animation_type}, frames {total_frames}, channels {len(channels_to_color)}")
            
        return {"success": True, "type": animation_type, "channels": len(channels_to_color)}
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error in animation setup: {str(e)}")
        return {"error": str(e)}

def NextAnimationFrame():
    """Render the next frame of the step animation
    
    Returns:
        dict: Result information including current frame
    """
    global step_animation, flMCPController
    
    try:
        # Check if animation is set up
        if not step_animation["channels"]:
            return {"success": False, "message": "No animation setup. Call AnimationSetup() first."}
        
        # Get animation state
        current_frame = step_animation["current_frame"]
        total_frames = step_animation["total_frames"]
        animation_type = step_animation["animation_type"]
        channels_to_color = step_animation["channels"]
        total_channels = len(channels_to_color)
        
        # Calculate progress (0.0 to 1.0)
        progress = current_frame / total_frames
        
        # Apply the appropriate animation type
        if animation_type == 0:  # Rainbow shift
            # Shifting rainbow where colors move across channels
            for pos, channel_idx in enumerate(channels_to_color):
                # Offset each channel's color by the progress amount to create movement
                hue = ((pos / total_channels) + progress) % 1.0
                
                if flMCPController:
                    r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                    r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = (b << 16) | (g << 8) | r
                    channels.setChannelColor(channel_idx, color)
        
        elif animation_type == 1:  # Pulse
            # All channels pulse together
            # Calculate brightness that pulses from 0.4 to 1.0
            brightness = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(progress * 2 * math.pi))
            
            for pos, channel_idx in enumerate(channels_to_color):
                # Each channel has a fixed hue but brightness changes
                hue = pos / total_channels
                
                if flMCPController:
                    r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, brightness)
                    r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = (b << 16) | (g << 8) | r
                    channels.setChannelColor(channel_idx, color)
        
        else:  # Color cycle - all channels change color together
            # All channels shift through the same color spectrum together
            hue = progress
            
            if flMCPController:
                r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                color = (b << 16) | (g << 8) | r
                
                for channel_idx in channels_to_color:
                    channels.setChannelColor(channel_idx, color)
        
        # Update the frame counter
        step_animation["current_frame"] = (current_frame + 1) % total_frames
        
        if flMCPController:
            flMCPController.log(f"Animation frame {current_frame}/{total_frames}")
            
        return {
            "success": True, 
            "frame": current_frame, 
            "total": total_frames,
            "progress": round(progress * 100),
            "type": animation_type
        }
        
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error rendering animation frame: {str(e)}")
        return {"error": str(e)}

def _RenderNextAnimationFrame():
    """Internal function to render next frame and schedule the next one"""
    global smooth_animation, flMCPController
    
    # Check if animation should still be running
    if not smooth_animation["is_running"] or smooth_animation["current_frame"] >= smooth_animation["end_frame"]:
        StopSmoothAnimation()
        return
    
    try:
        # Get animation state
        current_frame = smooth_animation["current_frame"]
        total_frames = smooth_animation["total_frames"]
        animation_type = smooth_animation["animation_type"]
        channels_to_color = smooth_animation["channels"]
        total_channels = len(channels_to_color)
        
        # Calculate progress (0.0 to 1.0)
        progress = current_frame / total_frames
        
        # Apply the appropriate animation type
        if animation_type == 0:  # Rainbow shift
            # Shifting rainbow where colors move across channels
            for pos, channel_idx in enumerate(channels_to_color):
                # Offset each channel's color by the progress amount to create movement
                hue = ((pos / total_channels) + progress) % 1.0
                
                if flMCPController:
                    r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                    r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = (b << 16) | (g << 8) | r
                    channels.setChannelColor(channel_idx, color)
        
        elif animation_type == 1:  # Pulse
            # All channels pulse together
            # Calculate brightness that pulses from 0.4 to 1.0
            brightness = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(progress * 2 * math.pi))
            
            for pos, channel_idx in enumerate(channels_to_color):
                # Each channel has a fixed hue but brightness changes
                hue = pos / total_channels
                
                if flMCPController:
                    r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, brightness)
                    r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = (b << 16) | (g << 8) | r
                    channels.setChannelColor(channel_idx, color)
        
        else:  # Color cycle - all channels change color together
            # All channels shift through the same color spectrum together
            hue = progress % 1.0
            
            if flMCPController:
                r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                color = (b << 16) | (g << 8) | r
                
                for channel_idx in channels_to_color:
                    channels.setChannelColor(channel_idx, color)
        
        # Update the frame counter
        smooth_animation["current_frame"] += 1
        
        # Schedule the next frame using a trick - we create a zero-task that can be
        # called again from the script output to simulate a timer loop
        if flMCPController:
            if smooth_animation["current_frame"] % 10 == 0:
                flMCPController.log(f"Animation progress: {smooth_animation['current_frame']}/{total_frames} frames")
            
        # Force a UI update by calling NextAnimationFrame again after a short delay
        # This uses FL Studio's own UI event loop
        ui.setHintMsg(f"Animation frame {smooth_animation['current_frame']}/{total_frames}")
        
        # Continue the animation by recursively calling this function
        # FL Studio will continue the script execution in the next UI cycle
        ui.afterIdle(_RenderNextAnimationFrame)
        
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error in animation frame: {str(e)}")
        smooth_animation["is_running"] = False

def RunSmoothAnimation(animation_type=0, selected_only=False, duration_seconds=5, frames_per_second=10):
    """Start a smooth animation that runs for the specified duration
    
    Args:
        animation_type (int): 0=rainbow shift, 1=pulse, 2=color cycle
        selected_only (bool): Only animate selected channels
        duration_seconds (float): How long the animation should run in seconds
        frames_per_second (int): How many frames to render per second
    """
    global smooth_animation, flMCPController
    
    try:
        # Stop any running animation
        StopSmoothAnimation()
        
        # Identify channels to animate
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        # Calculate total frames and frame delay
        total_frames = int(duration_seconds * frames_per_second)
        frame_delay = 1.0 / frames_per_second
        
        # Set up animation state
        smooth_animation = {
            "is_running": True,
            "start_time": time.time(),
            "frame_delay": frame_delay,
            "current_frame": 0,
            "total_frames": total_frames,
            "end_frame": total_frames,
            "animation_type": animation_type,
            "selected_only": selected_only,
            "channels": channels_to_color
        }
        
        if flMCPController:
            flMCPController.log(f"Starting smooth animation: {duration_seconds}s at {frames_per_second}fps ({total_frames} frames)")
        
        # Start the animation loop
        _RenderNextAnimationFrame()
        
        return {
            "success": True, 
            "type": animation_type,
            "frames": total_frames,
            "duration": duration_seconds
        }
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error starting smooth animation: {str(e)}")
        return {"error": str(e)}

def StopSmoothAnimation():
    """Stop any running smooth animation"""
    global smooth_animation, flMCPController
    
    if smooth_animation["is_running"]:
        smooth_animation["is_running"] = False
        duration = time.time() - smooth_animation["start_time"]
        
        if flMCPController:
            flMCPController.log(f"Stopped smooth animation after {duration:.2f}s")
        
        return {"success": True, "duration": duration}
    return {"success": False, "message": "No animation was running"}

def SingleCallAnimation(animation_type=0, selected_only=False, frames=30, delay_ms=30):
    """Run an animation in a single function call
    
    Args:
        animation_type (int): 0=rainbow shift, 1=pulse, 2=color cycle
        selected_only (bool): Only animate selected channels
        frames (int): Number of frames to render
        delay_ms (int): Delay between frames in milliseconds
    """
    try:
        # Identify channels to animate
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        total_to_color = len(channels_to_color)
        
        if flMCPController:
            flMCPController.log(f"Starting single-call animation with {frames} frames on {total_to_color} channels")
        
        # Run through frames
        start_time = time.time()
        for frame in range(frames):
            # Animation progress from 0.0 to 1.0
            progress = frame / frames
            
            # Show progress in hint bar
            progress_pct = int(progress * 100)
            ui.setHintMsg(f"Animation: {progress_pct}% complete (frame {frame+1}/{frames})")
            
            # Apply the appropriate animation type
            if animation_type == 0:  # Rainbow shift
                # Shifting rainbow where colors move across channels
                for pos, channel_idx in enumerate(channels_to_color):
                    hue = ((pos / total_to_color) + progress) % 1.0
                    
                    if flMCPController:
                        r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                        r, g, b = int(r * 255), int(g * 255), int(b * 255)
                        color = (b << 16) | (g << 8) | r
                        channels.setChannelColor(channel_idx, color)
            
            elif animation_type == 1:  # Pulse
                # Pulsing intensity synchronized across channels
                brightness = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(progress * 2 * math.pi))
                
                for pos, channel_idx in enumerate(channels_to_color):
                    hue = pos / total_to_color
                    
                    if flMCPController:
                        r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, brightness)
                        r, g, b = int(r * 255), int(g * 255), int(b * 255)
                        color = (b << 16) | (g << 8) | r
                        channels.setChannelColor(channel_idx, color)
            
            else:  # Color cycle - all channels change color together
                hue = progress
                
                if flMCPController:
                    r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                    r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = (b << 16) | (g << 8) | r
                    
                    for channel_idx in channels_to_color:
                        channels.setChannelColor(channel_idx, color)
            
            # Pause between frames to allow UI updates
            # Use a smaller delay for better animation frame rate
            time.sleep(delay_ms / 1000)
        
        # Clear the hint message
        ui.setHintMsg("")
        
        duration = time.time() - start_time
        if flMCPController:
            flMCPController.log(f"Completed animation in {duration:.2f}s")
        
        return {"success": True, "frames": frames, "duration": duration}
        
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error in animation: {str(e)}")
        return {"error": str(e)}

def AnimateRainbowWave(frames=60, delay_ms=30):
    """Run a rainbow wave animation in a single call
    
    Args:
        frames (int): Number of frames to render
        delay_ms (int): Delay between frames in milliseconds
    """
    return SingleCallAnimation(0, False, frames, delay_ms)

def AnimateRainbowPulse(frames=60, delay_ms=30):
    """Run a rainbow pulse animation in a single call
    
    Args:
        frames (int): Number of frames to render
        delay_ms (int): Delay between frames in milliseconds
    """
    return SingleCallAnimation(1, False, frames, delay_ms)

def AnimateColorCycle(frames=60, delay_ms=30):
    """Run a color cycle animation in a single call
    
    Args:
        frames (int): Number of frames to render
        delay_ms (int): Delay between frames in milliseconds
    """
    return SingleCallAnimation(2, False, frames, delay_ms)

# INSTANT EFFECTS
# These are single-shot visual effects that look good right away without animation

def RainbowPattern(selected_only=False):
    """Apply a rainbow pattern across channels
    
    Args:
        selected_only (bool): Only colorize selected channels
    """
    try:
        # Identify channels to color
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        total_to_color = len(channels_to_color)
        
        # Apply rainbow colors
        for pos, channel_idx in enumerate(channels_to_color):
            # Create a rainbow pattern based on position
            hue = pos / total_to_color
            
            if flMCPController:
                r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                color = (b << 16) | (g << 8) | r
                channels.setChannelColor(channel_idx, color)
        
        if flMCPController:
            flMCPController.log(f"Applied rainbow pattern to {total_to_color} channels")
        
        return {"success": True, "count": total_to_color}
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error applying rainbow pattern: {str(e)}")
        return {"error": str(e)}

def ColorGroups(selected_only=False, groups=4):
    """Color channels in distinct groups
    
    Args:
        selected_only (bool): Only colorize selected channels
        groups (int): Number of color groups
    """
    try:
        # Identify channels to color
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        total_to_color = len(channels_to_color)
        
        # Generate a set of distinct colors
        group_colors = []
        for g in range(groups):
            # Use evenly spaced hues for maximum color difference
            hue = g / groups
            # Generate saturated, bright colors
            if flMCPController:
                r, g, b = flMCPController._hsv_to_rgb(hue, 0.9, 0.9)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                color = (b << 16) | (g << 8) | r
                group_colors.append(color)
        
        # Apply colors in groups
        for pos, channel_idx in enumerate(channels_to_color):
            # Determine which group this channel belongs to
            group = pos % groups
            # Apply the color for this group
            channels.setChannelColor(channel_idx, group_colors[group])
        
        if flMCPController:
            flMCPController.log(f"Applied {groups} color groups to {total_to_color} channels")
        
        return {"success": True, "count": total_to_color, "groups": groups}
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error applying color groups: {str(e)}")
        return {"error": str(e)}

def RandomColors(selected_only=False, brightness=0.9):
    """Apply random colors to channels
    
    Args:
        selected_only (bool): Only colorize selected channels
        brightness (float): Brightness of colors (0.0-1.0)
    """
    try:
        # Identify channels to color
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        total_to_color = len(channels_to_color)
        
        # Apply random colors
        for channel_idx in channels_to_color:
            # Generate random color with specified brightness
            r = int(random.uniform(0, brightness) * 255)
            g = int(random.uniform(0, brightness) * 255)
            b = int(random.uniform(0, brightness) * 255)
            
            # Make sure colors are reasonably bright
            max_component = max(r, g, b)
            if max_component < 100:
                scale = 100 / max_component if max_component > 0 else 1
                r = min(255, int(r * scale))
                g = min(255, int(g * scale))
                b = min(255, int(b * scale))
            
            color = (b << 16) | (g << 8) | r
            channels.setChannelColor(channel_idx, color)
        
        if flMCPController:
            flMCPController.log(f"Applied random colors to {total_to_color} channels")
        
        return {"success": True, "count": total_to_color}
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error applying random colors: {str(e)}")
        return {"error": str(e)}

def ColorByType(selected_only=False):
    """Color channels based on their type (instruments, samplers, effects)
    
    Args:
        selected_only (bool): Only colorize selected channels
    """
    try:
        # Identify channels to color
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        total_to_color = len(channels_to_color)
        
        # Define colors for different channel types
        # We'll use names from channel.getChannelName to guess the type
        colors = {
            "synth": 0x2090FF,     # Blue for synths
            "bass": 0x3050FF,      # Purple for bass
            "drum": 0xFF5050,      # Red for drums
            "kick": 0xFF5050,      # Red for kick
            "snare": 0xFF9090,     # Light red for snare
            "hat": 0xFFB060,       # Orange for hats
            "perc": 0xFFA030,      # Orange for percussion
            "vocal": 0x60D060,     # Green for vocals
            "vox": 0x60D060,       # Green for vocals
            "guitar": 0xFFD030,    # Yellow for guitar
            "piano": 0x60FFFF,     # Cyan for piano
            "key": 0x60FFFF,       # Cyan for keyboards
            "pad": 0xB090FF,       # Purple for pads
            "lead": 0xFF60A0,      # Pink for leads
            "fx": 0xAFAFAF,        # Gray for FX
            "default": 0xFFFFFF    # White default
        }
        
        # Apply colors based on channel names
        for channel_idx in channels_to_color:
            # Get the channel name and convert to lowercase
            name = channels.getChannelName(channel_idx).lower()
            
            # Try to find a matching type
            found_type = False
            for type_name, color in colors.items():
                if type_name in name:
                    channels.setChannelColor(channel_idx, color)
                    found_type = True
                    break
            
            # Use default color if no match found
            if not found_type:
                channels.setChannelColor(channel_idx, colors["default"])
        
        if flMCPController:
            flMCPController.log(f"Applied type-based colors to {total_to_color} channels")
        
        return {"success": True, "count": total_to_color}
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error in color by type: {str(e)}")
        return {"error": str(e)}

def GradientPreset(preset=0, selected_only=False):
    """Apply a preset gradient to channels
    
    Args:
        preset (int): 0=sunset, 1=ocean, 2=forest, 3=fire, 4=neon
        selected_only (bool): Only colorize selected channels
    """
    try:
        # Identify channels to color
        channels_to_color = []
        total_channels = channels.channelCount()
        
        for i in range(total_channels):
            if selected_only and not channels.isChannelSelected(i):
                continue
            channels_to_color.append(i)
            
        if not channels_to_color:
            return {"success": False, "message": "No channels to color"}
        
        total_to_color = len(channels_to_color)
        
        # Define gradient presets - each is a list of colors to interpolate between
        presets = [
            # 0: Sunset - orange to purple
            [(255, 100, 0), (255, 0, 100), (150, 0, 255)],
            
            # 1: Ocean - aqua to deep blue
            [(0, 255, 255), (0, 100, 255), (0, 0, 150)],
            
            # 2: Forest - yellow-green to deep green
            [(180, 255, 0), (30, 200, 0), (0, 100, 0)],
            
            # 3: Fire - yellow to red
            [(255, 255, 0), (255, 150, 0), (255, 0, 0)],
            
            # 4: Neon - bright colors
            [(255, 0, 255), (0, 255, 255), (255, 255, 0)]
        ]
        
        # Get the selected preset
        preset_index = preset % len(presets)
        gradient_colors = presets[preset_index]
        
        # Apply gradient colors
        for i, channel_idx in enumerate(channels_to_color):
            # Calculate position in gradient (0.0 to 1.0)
            pos = i / max(1, total_to_color - 1)
            
            # Interpolate between gradient colors
            segment_count = len(gradient_colors) - 1
            segment_pos = pos * segment_count
            segment_index = min(int(segment_pos), segment_count - 1)
            segment_offset = segment_pos - segment_index
            
            # Get the two colors to interpolate between
            color1 = gradient_colors[segment_index]
            color2 = gradient_colors[segment_index + 1]
            
            # Linear interpolation between colors
            r = int(color1[0] + segment_offset * (color2[0] - color1[0]))
            g = int(color1[1] + segment_offset * (color2[1] - color1[1]))
            b = int(color1[2] + segment_offset * (color2[2] - color1[2]))
            
            # Convert to FL Studio color format (0xBBGGRR)
            color = (b << 16) | (g << 8) | r
            channels.setChannelColor(channel_idx, color)
        
        preset_names = ["Sunset", "Ocean", "Forest", "Fire", "Neon"]
        preset_name = preset_names[preset_index]
        
        if flMCPController:
            flMCPController.log(f"Applied {preset_name} gradient to {total_to_color} channels")
        
        return {"success": True, "count": total_to_color, "preset": preset_name}
    except Exception as e:
        if flMCPController:
            flMCPController.log(f"Error applying gradient: {str(e)}")
        return {"error": str(e)}
