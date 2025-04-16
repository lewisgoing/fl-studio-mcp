"""
Visual commands and color animations for FL Studio MCP Controller
"""

import channels
import random
import math
import time
import ui

def randomize_channel_colors(selected_only=False):
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
        
        return {"success": True, "count": count}
    except Exception as e:
        print(f"Error randomizing colors: {str(e)}")
        return {"error": str(e)}

def hsv_to_rgb(h, s, v):
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

def cmd_randomize_colors(params):
    """Randomize channel colors in the channel rack"""
    try:
        # Get parameters
        selected_only = params.get("value", 0) > 0
        
        # Call the randomize function
        result = randomize_channel_colors(selected_only)
        
        return result
    except Exception as e:
        print(f"Error in randomize_colors: {str(e)}")
        return {"error": str(e)}

# --- Step Animation Functions ---

def animation_setup(animation_type=0, selected_only=False, total_frames=30):
    """Set up a step-by-step animation that can be manually advanced
    
    Args:
        animation_type (int): 0=rainbow shift, 1=pulse, 2=color cycle
        selected_only (bool): Only animate selected channels
        total_frames (int): Total number of frames in the animation
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
        
        # Create animation state
        animation_state = {
            "current_frame": 0,
            "total_frames": total_frames,
            "animation_type": animation_type,
            "selected_only": selected_only,
            "channels": channels_to_color
        }
        
        return {"success": True, "type": animation_type, "channels": len(channels_to_color), "state": animation_state}
    except Exception as e:
        print(f"Error in animation setup: {str(e)}")
        return {"error": str(e)}

def next_animation_frame(animation_state):
    """Render the next frame of the step animation
    
    Args:
        animation_state (dict): Animation state dictionary
    
    Returns:
        dict: Result information including current frame
    """
    try:
        # Check if animation is set up
        if not animation_state["channels"]:
            return {"success": False, "message": "No animation setup."}
        
        # Get animation state
        current_frame = animation_state["current_frame"]
        total_frames = animation_state["total_frames"]
        animation_type = animation_state["animation_type"]
        channels_to_color = animation_state["channels"]
        total_channels = len(channels_to_color)
        
        # Calculate progress (0.0 to 1.0)
        progress = current_frame / total_frames
        
        # Apply the appropriate animation type
        if animation_type == 0:  # Rainbow shift
            # Shifting rainbow where colors move across channels
            for pos, channel_idx in enumerate(channels_to_color):
                # Offset each channel's color by the progress amount to create movement
                hue = ((pos / total_channels) + progress) % 1.0
                
                r, g, b = hsv_to_rgb(hue, 0.9, 0.9)
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
                
                r, g, b = hsv_to_rgb(hue, 0.9, brightness)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                color = (b << 16) | (g << 8) | r
                channels.setChannelColor(channel_idx, color)
        
        else:  # Color cycle - all channels change color together
            # All channels shift through the same color spectrum together
            hue = progress
            
            r, g, b = hsv_to_rgb(hue, 0.9, 0.9)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            color = (b << 16) | (g << 8) | r
            
            for channel_idx in channels_to_color:
                channels.setChannelColor(channel_idx, color)
        
        # Update the frame counter
        animation_state["current_frame"] = (current_frame + 1) % total_frames
        
        return {
            "success": True, 
            "frame": current_frame, 
            "total": total_frames,
            "progress": round(progress * 100),
            "type": animation_type
        }
        
    except Exception as e:
        print(f"Error rendering animation frame: {str(e)}")
        return {"error": str(e)}

# --- Smooth Animation Functions ---

def run_smooth_animation(animation_type=0, selected_only=False, duration_seconds=5, frames_per_second=10):
    """Start a smooth animation that runs for the specified duration
    
    Args:
        animation_type (int): 0=rainbow shift, 1=pulse, 2=color cycle
        selected_only (bool): Only animate selected channels
        duration_seconds (float): How long the animation should run in seconds
        frames_per_second (int): How many frames to render per second
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
        
        # Calculate total frames and frame delay
        total_frames = int(duration_seconds * frames_per_second)
        frame_delay = 1.0 / frames_per_second
        
        # Set up animation state
        animation_state = {
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
        
        # Start the animation loop
        # Note: In a real implementation, this would need to be triggered by a separate UI timer
        # or by FL Studio's OnIdle mechanism
        
        return {
            "success": True, 
            "type": animation_type,
            "frames": total_frames,
            "duration": duration_seconds,
            "state": animation_state
        }
    except Exception as e:
        print(f"Error starting smooth animation: {str(e)}")
        return {"error": str(e)}

def render_animation_frame(animation_state):
    """Render a frame of animation based on the animation state
    
    Args:
        animation_state (dict): Animation state dictionary
        
    Returns:
        bool: True if animation should continue, False if finished
    """
    # Check if animation should still be running
    if not animation_state["is_running"] or animation_state["current_frame"] >= animation_state["end_frame"]:
        return False
    
    try:
        # Get animation state
        current_frame = animation_state["current_frame"]
        total_frames = animation_state["total_frames"]
        animation_type = animation_state["animation_type"]
        channels_to_color = animation_state["channels"]
        total_channels = len(channels_to_color)
        
        # Calculate progress (0.0 to 1.0)
        progress = current_frame / total_frames
        
        # Apply the appropriate animation type
        if animation_type == 0:  # Rainbow shift
            # Shifting rainbow where colors move across channels
            for pos, channel_idx in enumerate(channels_to_color):
                # Offset each channel's color by the progress amount to create movement
                hue = ((pos / total_channels) + progress) % 1.0
                
                r, g, b = hsv_to_rgb(hue, 0.9, 0.9)
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
                
                r, g, b = hsv_to_rgb(hue, 0.9, brightness)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                color = (b << 16) | (g << 8) | r
                channels.setChannelColor(channel_idx, color)
        
        else:  # Color cycle - all channels change color together
            # All channels shift through the same color spectrum together
            hue = progress % 1.0
            
            r, g, b = hsv_to_rgb(hue, 0.9, 0.9)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            color = (b << 16) | (g << 8) | r
            
            for channel_idx in channels_to_color:
                channels.setChannelColor(channel_idx, color)
        
        # Update the frame counter
        animation_state["current_frame"] += 1
        
        # Show progress in hint bar
        if animation_state["current_frame"] % 10 == 0:
            ui.setHintMsg(f"Animation frame {animation_state['current_frame']}/{total_frames}")
        
        return True
        
    except Exception as e:
        print(f"Error in animation frame: {str(e)}")
        animation_state["is_running"] = False
        return False

def stop_animation(animation_state):
    """Stop any running animation
    
    Args:
        animation_state (dict): Animation state dictionary
    """
    if animation_state["is_running"]:
        animation_state["is_running"] = False
        duration = time.time() - animation_state["start_time"]
        
        return {"success": True, "duration": duration}
    return {"success": False, "message": "No animation was running"}

# --- Instant Effects (Single-Call Visual Effects) ---

def rainbow_pattern(selected_only=False):
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
            
            r, g, b = hsv_to_rgb(hue, 0.9, 0.9)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            color = (b << 16) | (g << 8) | r
            channels.setChannelColor(channel_idx, color)
        
        return {"success": True, "count": total_to_color}
    except Exception as e:
        print(f"Error applying rainbow pattern: {str(e)}")
        return {"error": str(e)}

def color_groups(selected_only=False, groups=4):
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
            r, g, b = hsv_to_rgb(hue, 0.9, 0.9)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            color = (b << 16) | (g << 8) | r
            group_colors.append(color)
        
        # Apply colors in groups
        for pos, channel_idx in enumerate(channels_to_color):
            # Determine which group this channel belongs to
            group = pos % groups
            # Apply the color for this group
            channels.setChannelColor(channel_idx, group_colors[group])
        
        return {"success": True, "count": total_to_color, "groups": groups}
    except Exception as e:
        print(f"Error applying color groups: {str(e)}")
        return {"error": str(e)}

def random_colors(selected_only=False, brightness=0.9):
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
        
        return {"success": True, "count": total_to_color}
    except Exception as e:
        print(f"Error applying random colors: {str(e)}")
        return {"error": str(e)}

def color_by_type(selected_only=False):
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
        
        return {"success": True, "count": total_to_color}
    except Exception as e:
        print(f"Error in color by type: {str(e)}")
        return {"error": str(e)}

def gradient_preset(preset=0, selected_only=False):
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
        
        return {"success": True, "count": total_to_color, "preset": preset_name}
    except Exception as e:
        print(f"Error applying gradient: {str(e)}")
        return {"error": str(e)} 