# FL Studio MCP Integration Setup Guide

This guide will help you set up the FL Studio MCP (Model Context Protocol) integration, allowing Claude AI to control FL Studio through MIDI.

## Overview of Changes

We've made significant improvements to the MCP server and FL Studio controller script to better match FL Studio's capabilities:

1. **Simplified MIDI protocol** - Now using a more direct approach that FL Studio can interpret more reliably
2. **Enhanced error handling** - Better logging and fallbacks for more stable operation
3. **FL Studio-specific commands** - Adapted to use FL Studio's API more effectively
4. **Multiple command paths** - Using both direct MIDI messages and our command protocol for redundancy

## Setup Instructions

### Step 1: Set up the IAC Driver in macOS

1. Open **Audio MIDI Setup** (you can find it in Applications/Utilities or search with Spotlight)
2. Click **Window > Show MIDI Studio** if the MIDI studio is not already visible
3. Double-click on the **IAC Driver** icon
4. Check **Device is online**
5. Create a port named **IAC Driver MCP Bridge** if it doesn't already exist
6. Click **Apply** and close the window

### Step 2: Install the MCP Server

1. Clone the repository
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
   or 
   ```
   uv install
   ```
3. Place `flstudio_mcp_iac/server.py` in the correct location in the project structure

### Step 3: Install the FL Studio Controller Script

1. Navigate to your FL Studio MIDI scripts folder:
   - **Windows**: `C:\Program Files\Image-Line\FL Studio 21\System\Hardware\`
   - **macOS**: `/Applications/FL Studio.app/Contents/Resources/FL/System/Hardware/`

2. Create a new folder called `FL Studio MCP Controller`
3. Copy `device_test.py` to this folder, but rename it to `device_test.py` as that's what FL Studio expects

### Step 4: Configure FL Studio

1. Open FL Studio
2. Go to **Options > MIDI Settings**
3. Find **IAC Driver MCP Bridge** in the input devices list
4. Enable it and select **FL Studio MCP Controller** as the controller type
5. Make sure the port is enabled (highlighted)
6. Click **Refresh** if the controller doesn't appear immediately

### Step 5: Run the MCP Server

1. Run the server using the provided script:
   ```
   ./run_flstudio_mcp.sh
   ```
   or directly with:
   ```
   python -m flstudio_mcp_iac.server
   ```

2. You should see log messages indicating that the server has started and connected to the IAC Driver port

### Step 6: Test the Connection

1. In the MCP server terminal, you should see logs when FL Studio receives MIDI messages
2. In FL Studio, you should see log messages in the output window/console with the `[MCP]` prefix

## Troubleshooting

### MIDI Connection Issues

- Make sure the IAC Driver is online in Audio MIDI Setup
- Ensure the correct MIDI port is selected in FL Studio's MIDI settings
- Check for any error messages in the MCP server logs

### FL Studio Not Responding to Commands

- Make sure the FL Studio MCP Controller is properly loaded (you should see initialization logs)
- Try restarting FL Studio and the MCP server
- Enable debug mode in the controller script by setting `DEBUG = True`

### Error Messages in the Server

- Check that all required packages are installed
- Verify that the IAC Driver port is properly configured
- Ensure FL Studio is running before starting the server

## Feature Support

The integration now supports:

- ✅ Getting MIDI ports
- ✅ Playing notes
- ✅ Selecting patterns
- ✅ Controlling playback (play/stop/record)
- ✅ Creating tracks
- ✅ Loading instruments
- ✅ Setting tempo (BPM)
- ✅ Creating MIDI clips
- ✅ Creating chord progressions
- ✅ Setting mixer levels
- ✅ Direct FL Studio commands (undo, redo, window management)

## Advanced Usage

### Custom Commands

You can extend the system with custom commands by:

1. Adding new functions to the MCP server (`server.py`)
2. Adding corresponding handlers in the FL Studio controller script (`device_test.py`)

### MIDI Mapping

FL Studio's MIDI mapping capabilities can be used alongside this integration:

1. Go to **Tools > MIDI > Map MIDI controllers** in FL Studio
2. Assign controls to different parameters
3. These mappings will work alongside our dedicated command protocol

## Examples

Here are some examples of how to use the MCP server:

```python
# Play a C major chord
play_note(60, 100, 1)  # C
play_note(64, 100, 1)  # E
play_note(67, 100, 1)  # G

# Create a simple chord progression
create_chord_progression(["C", "G", "Am", "F"], octave=4)

# Control transport
control_transport("play")
control_transport("stop")

# Create a new track
create_track("Bass", "instrument")
load_instrument("bass")
```