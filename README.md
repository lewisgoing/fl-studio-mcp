# FL Studio MCP Integration v2.0

This guide will help you set up the FL Studio MCP (Model Context Protocol) integration v2.0, allowing Claude AI to control FL Studio through MIDI with advanced music production capabilities.

## Overview of Changes

The v2.0 release includes significant enhancements to the MCP server and FL Studio controller script:

1. **Dual-protocol architecture**:
   - **CC-based protocol** for simple commands (play, stop, etc.)
   - **SysEx-based protocol** for complex data-heavy operations (chord progressions, melodies, etc.)

2. **Advanced music production features**:
   - Chord progression generation
   - Melody creation based on scales
   - Parameter automation
   - Arrangement control
   - Enhanced status feedback

3. **Infrastructure improvements**:
   - More robust error handling
   - Better MIDI communication
   - Structured feedback mechanism
   - Music theory implementation (scales, chords, progressions)

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
3. Make sure `flstudio_mcp_iac/server.py` is in the correct location in the project structure

### Step 3: Install the FL Studio Controller Script

1. Navigate to your FL Studio MIDI scripts folder:
   - **Windows**: `C:\Program Files\Image-Line\FL Studio 21\System\Hardware\`
   - **macOS**: `/Applications/FL Studio.app/Contents/Resources/FL/System/Hardware/`

2. Create a new folder called `FL Studio MCP Controller`
3. Copy `device_flstudiocontroller.py` to this folder

### Step 4: Configure FL Studio

1. Open FL Studio
2. Go to **Options > MIDI Settings**
3. Find **IAC Driver MCP Bridge** in the input devices list
4. Enable it and select **FL Studio MCP Controller v2.0** as the controller type
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

## New Features

### Chord Progressions

Create chord progressions like C-G-Am-F directly in FL Studio:

```python
# Create a C major chord progression
create_chord_progression(
    progression=["C", "G", "Am", "F"],
    duration_beats=4,
    channel=0,
    velocity=100
)

# Create a jazz progression with 7th chords
create_chord_progression(
    progression=["Cmaj7", "Dm7", "G7", "Cmaj7"],
    duration_beats=2
)
```

### Melody Generation

Generate melodies based on musical scales:

```python
# Create a melody in C major
create_melody(
    scale="C major",
    length=8,
    channel=1,
    velocity=90
)

# Create a pentatonic melody
create_melody(
    scale="A pentatonicminor",
    length=16,
    channel=2,
    seed=42  # Use a seed for reproducible melodies
)
```

### Parameter Automation

Automate plugin parameters over time:

```python
# Automate filter cutoff
automate_parameter(
    track_index=1,
    plugin_index=0,
    parameter_index=12,  # Cutoff parameter
    points=[(0, 0.2), (4, 0.8), (8, 0.4), (16, 0.2)]  # (time, value) pairs
)
```

### Arrangement Control

Control the pattern sequence and looping:

```python
# Set up a pattern sequence with loop points
set_arrangement(
    pattern_sequence=[0, 1, 2, 3],
    loop_start=0,
    loop_end=4
)
```

### Enhanced Status Feedback

Get detailed status information from FL Studio:

```python
# Get current status (tempo, playback state, etc.)
status = get_status()
print(f"Current tempo: {status['data']['tempo']} BPM")
print(f"Playing: {status['data']['playing']}")
```

## API Reference

### Basic Commands (CC-based)

| Command | Description |
|---------|-------------|
| `play_note(note, velocity, duration)` | Play a single MIDI note |
| `create_track(name, track_type)` | Create a new track |
| `load_instrument(instrument_name, channel)` | Load an instrument |
| `set_tempo(bpm)` | Set the project tempo |
| `control_transport(action)` | Control playback (play/stop/record) |
| `select_pattern(pattern)` | Select a pattern by number |
| `set_mixer_level(track, level)` | Set mixer track volume |
| `select_channel(channel)` | Select a channel in the Channel Rack |
| `add_audio_effect(track, effect_type)` | Add an audio effect to a mixer track |

### Advanced Commands (SysEx-based)

| Command | Description |
|---------|-------------|
| `create_chord_progression(progression, duration_beats, channel, velocity)` | Create a chord progression |
| `create_melody(scale, length, channel, velocity, seed)` | Generate a melody based on a scale |
| `automate_parameter(track_index, plugin_index, parameter_index, points)` | Automate a plugin parameter |
| `set_arrangement(pattern_sequence, loop_start, loop_end)` | Set the pattern sequence and loop points |
| `get_status()` | Get detailed project status |

## Supported Chords

The system supports the following chord types:

- Major: `"C"`, `"G"`, etc.
- Minor: `"Cm"`, `"Am"`, etc.
- Dominant 7th: `"C7"`, `"G7"`, etc.
- Major 7th: `"Cmaj7"`, `"Gmaj7"`, etc.
- Minor 7th: `"Cm7"`, `"Am7"`, etc.
- Diminished: `"Cdim"`, `"Bdim"`, etc.
- Augmented: `"Caug"`, `"Faug"`, etc.
- Suspended 4th: `"Csus4"`, `"Gsus4"`, etc.
- Suspended 2nd: `"Csus2"`, `"Dsus2"`, etc.

## Supported Scales

The system supports the following scale types:

- Major: `"C major"`, `"G major"`, etc.
- Minor: `"A minor"`, `"E minor"`, etc.
- Harmonic Minor: `"A harmonicminor"`, etc.
- Melodic Minor: `"D melodicminor"`, etc.
- Dorian: `"D dorian"`, etc.
- Phrygian: `"E phrygian"`, etc.
- Lydian: `"F lydian"`, etc.
- Mixolydian: `"G mixolydian"`, etc.
- Locrian: `"B locrian"`, etc.
- Pentatonic Major: `"C pentatonicmajor"`, etc.
- Pentatonic Minor: `"A pentatonicminor"`, etc.
- Blues: `"E blues"`, etc.

## Advanced Usage

### Custom Commands

You can extend the system with custom commands by:

1. Adding new functions to the MCP server (`server.py`)
2. Adding corresponding handlers in the FL Studio controller script (`device_flstudiocontroller.py`)
3. Implementing the SysEx parsing/handling for complex commands

### Creating Complex Musical Progressions

```python
# Create a verse-chorus arrangement
# Verse: Am-F-C-G
# Chorus: C-G-Am-F
verse = ["Am", "F", "C", "G"]
chorus = ["C", "G", "Am", "F"]

# Create verse
create_chord_progression(verse, duration_beats=4, channel=0)

# Create chorus
select_pattern(1)  # Move to next pattern
create_chord_progression(chorus, duration_beats=4, channel=0)

# Set arrangement
set_arrangement([0, 0, 1, 1, 0, 1, 1, 1], loop_start=0, loop_end=8)
```

### Generating Lead Melodies Over Chord Progressions

```python
# Create chord progression
create_chord_progression(["C", "G", "Am", "F"], duration_beats=4, channel=0)

# Create compatible melody on another channel
create_melody(scale="C major", length=16, channel=1)
```

## Troubleshooting

### MIDI Connection Issues

- Make sure the IAC Driver is online in Audio MIDI Setup
- Ensure the correct MIDI port is selected in FL Studio's MIDI settings
- Check for any error messages in the MCP server logs

### FL Studio Not Responding to Commands

- Make sure the FL Studio MCP Controller is properly loaded (you should see initialization logs)
- Try restarting FL Studio and the MCP server
- Enable debug mode in the controller script by setting `DEBUG = True`

### SysEx Message Errors

- Check that message sizes aren't too large (some MIDI implementations have size limits)
- Verify that the command ID matches between server and controller
- Ensure proper JSON formatting for complex command data

## Known Limitations

- **Piano roll editing**: Due to FL Studio's API limitations, some piano roll operations might not produce perfect results
- **Plugin automation**: Some parameters might not be automatable depending on the plugin
- **Real-time feedback**: There might be a slight delay in feedback from FL Studio
- **Complex arrangements**: Very large pattern sequences might require breaking into smaller chunks

## Future Enhancements

- **Machine learning-based melody generation**: Implementation of ML models for more musical melodies
- **Audio analysis feedback**: Integration with audio analysis for more intelligent automation
- **Template support**: Save and load creative templates for quick composition
- **Multi-device support**: Coordination with other MIDI controllers