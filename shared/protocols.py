# shared/protocols.py
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger('flstudio-mcp.protocol')

# Use a unique identifier for your SysEx messages
# (You can register for an official one, or use a custom one like 0x7D)
SYSEX_HEADER: bytes = bytes([0xF0, 0x7D, 0x01]) # Start (F0), Custom ID (7D), Your Product ID (01)
SYSEX_END: int = 0xF7

# Define Command IDs (replace your current integer types 1-13)
class Command:
    # Channel Commands
    GET_CHANNEL_NAMES = 0x10
    GET_CHANNEL_NAME_BY_INDEX = 0x11
    SET_CHANNEL_COLOR = 0x12
    RANDOMIZE_COLORS = 0x13
    GET_CHANNEL_COUNT = 0x14
    IS_CHANNEL_SELECTED = 0x15
    SELECT_CHANNEL = 0x16
    GET_CHANNEL_VOLUME = 0x17
    SET_CHANNEL_VOLUME = 0x18
    GET_CHANNEL_PAN = 0x19
    SET_CHANNEL_PAN = 0x1A
    IS_CHANNEL_MUTED = 0x1B
    SET_CHANNEL_MUTE = 0x1C
    IS_CHANNEL_SOLO = 0x1D
    SET_CHANNEL_SOLO = 0x1E
    # ... add more channel commands as needed

    # Mixer Commands
    SET_MIXER_LEVEL = 0x20
    ADD_AUDIO_EFFECT = 0x21
    GET_MIXER_TRACK_COUNT = 0x22
    GET_MIXER_LEVEL = 0x23
    # ... add more mixer commands

    # Transport Commands
    SET_TEMPO = 0x30
    GET_TEMPO = 0x31
    TRANSPORT_CONTROL = 0x32 # (play, stop, record, toggle_play)
    GET_IS_PLAYING = 0x33
    SELECT_PATTERN = 0x34
    GET_CURRENT_PATTERN = 0x35
    # ... add more transport commands

    # Response/Feedback Commands (Device -> Server)
    RESPONSE_SUCCESS = 0x70 # Indicates successful execution, data may be included
    RESPONSE_ERROR = 0x71   # Indicates an error occurred during execution
    ASYNC_UPDATE = 0x7F     # For unsolicited updates from FL (e.g., tempo change)

    # --- Placeholder for future/unimplemented ---
    # CREATE_NOTES = 0x01 (from old protocol - map if needed)
    # CREATE_TRACK = 0x02
    # LOAD_INSTRUMENT = 0x03
    # CREATE_CHORD_PROGRESSION = 0x08
    # ADD_MIDI_EFFECT = 0x09


def encode_sysex(command_id: int, data: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Encodes a command ID and associated data dictionary into a SysEx message.
    Includes the necessary SysEx start (F0), header, command ID, JSON payload, and end (F7).
    """
    payload_bytes = b''
    if data:
        try:
            # Convert data dict to compact JSON string, then encode to UTF-8 bytes
            payload_str = json.dumps(data, separators=(',', ':'))
            payload_bytes = payload_str.encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode data {data} to JSON: {e}")
            # Decide how to handle encoding errors: send command without data or raise?
            # Sending without data might lead to unexpected behavior on the receiver.
            # Raising might be better, or returning an empty byte string.
            return b'' # Return empty bytes to indicate failure

    # --- SysEx Data Byte Escaping (Crucial!) ---
    # MIDI SysEx data bytes (between F0 and F7) must be <= 127 (0x7F).
    # Bytes >= 128 (0x80) or the F7 byte itself need encoding.
    # A common method is 7-bit encoding or using escape sequences.
    # Let's implement a simple 7-bit encoding:
    # Each 7 bytes of original data become 8 bytes of encoded data.
    # The 8th byte contains the MSBs of the preceding 7 bytes.
    encoded_payload = bytearray()
    original_len = len(payload_bytes)
    i = 0
    while i < original_len:
        msb_byte = 0
        temp_buffer = bytearray()
        # Process up to 7 bytes at a time
        for j in range(7):
            if i + j < original_len:
                byte = payload_bytes[i + j]
                if byte >= 128: # Check if MSB is set
                     # This basic implementation doesn't handle bytes >= 128 well.
                     # A more robust method like COBS or SLIP might be needed
                     # or ensure JSON only contains ASCII characters.
                     logger.error(f"SysEx payload contains byte >= 128 (0x{byte:02X}). 7-bit encoding needed or restrict payload.")
                     # For now, we'll skip bytes >= 128, which will likely break JSON parsing
                     # Consider base64 encoding the JSON string *before* this step
                     # or using a library that handles MIDI SysEx encoding.
                     temp_buffer.append(byte & 0x7F) # Append lower 7 bits (data likely corrupted)
                     msb_byte |= (1 << j) # Mark that the original byte had MSB set
                else:
                    temp_buffer.append(byte) # Append original byte (0-127)
            else:
                temp_buffer.append(0) # Pad if fewer than 7 bytes remain in block

        # Prepend the MSB byte to the block of 7 data bytes
        encoded_payload.append(msb_byte)
        encoded_payload.extend(temp_buffer)
        i += 7

    # Check encoded payload size (MIDI SysEx often has practical limits, e.g., 256 bytes)
    if len(encoded_payload) > 240: # Conservative limit
        logger.warning(f"Encoded SysEx payload is large ({len(encoded_payload)} bytes). May exceed buffer limits.")
        # Implement message chunking if large payloads are expected.

    # Assemble the final SysEx message
    full_message = SYSEX_HEADER + bytes([command_id]) + encoded_payload + bytes([SYSEX_END])
    return full_message


def decode_sysex(message: bytes) -> Optional[Dict[str, Any]]:
    """
    Decodes a SysEx message (expected to be 7-bit encoded) back into
    command ID and data dictionary.
    """
    if not message or message[-1] != SYSEX_END or not message.startswith(SYSEX_HEADER):
        logger.error("Invalid SysEx message format: Missing header, end, or empty.")
        return None

    header_len = len(SYSEX_HEADER)
    # Check if message is long enough for header + command_id + end_byte (at least)
    if len(message) < header_len + 2:
         logger.error("SysEx message too short to contain command ID.")
         return None

    command_id = message[header_len]
    encoded_payload = message[header_len + 1:-1] # Data between command ID and F7

    # --- Decode 7-bit Encoded Payload ---
    decoded_payload = bytearray()
    encoded_len = len(encoded_payload)
    i = 0
    while i < encoded_len:
        # Check if there's a full block (MSB byte + 7 data bytes)
        if i + 8 > encoded_len:
            logger.error("Invalid 7-bit encoded payload length.")
            break # Stop decoding

        msb_byte = encoded_payload[i]
        # Extract the 7 data bytes
        for j in range(7):
            data_byte = encoded_payload[i + 1 + j]
            # Reconstruct the original byte using the MSB information
            if (msb_byte >> j) & 1:
                # This byte originally had its MSB set
                # THIS IS WHERE THE ASSUMPTION BREAKS - we don't know the original MSB value
                # unless we are strictly encoding ASCII. If non-ASCII was encoded,
                # we cannot perfectly reconstruct it here without a better scheme.
                # Assuming ASCII for now (or potentially corrupted data)
                original_byte = data_byte # | 0x80 # Uncommenting this assumes original was >= 128
                if original_byte >= 128:
                     logger.warning(f"Decoded byte >= 128 ({original_byte}) - potential data corruption if non-ASCII was encoded.")
            else:
                original_byte = data_byte # Original byte was 0-127

            decoded_payload.append(original_byte)
        i += 8

    # Attempt to remove potential padding (often null bytes if original length wasn't multiple of 7)
    # This is heuristic - a length prefix would be more reliable
    while decoded_payload and decoded_payload[-1] == 0:
         decoded_payload.pop()


    # --- Parse JSON from Decoded Payload ---
    data = None
    if decoded_payload:
        try:
            payload_str = decoded_payload.decode('utf-8')
            # Remove potential trailing null characters that might interfere with JSON
            payload_str = payload_str.rstrip('\x00')
            if payload_str: # Avoid parsing empty string
                 data = json.loads(payload_str)
            else:
                 data = {} # Treat empty payload as empty dict

        except json.JSONDecodeError as e:
            payload_preview = decoded_payload[:50].hex() + ('...' if len(decoded_payload) > 50 else '')
            logger.error(f"Failed to decode JSON from payload. Error: {e}. Payload(hex): {payload_preview}")
            # Return command ID but indicate data error
            return {"command_id": command_id, "error": "JSON Decode Error", "raw_payload_hex": decoded_payload.hex()}
        except UnicodeDecodeError as e:
             payload_preview = decoded_payload[:50].hex() + ('...' if len(decoded_payload) > 50 else '')
             logger.error(f"Failed to decode UTF-8 from payload. Error: {e}. Payload(hex): {payload_preview}")
             return {"command_id": command_id, "error": "UTF-8 Decode Error", "raw_payload_hex": decoded_payload.hex()}
        except Exception as e:
            logger.exception(f"Unexpected error decoding SysEx payload: {e}")
            return {"command_id": command_id, "error": str(e)}
    else:
         data = {} # No payload bytes after decoding

    return {"command_id": command_id, "data": data}