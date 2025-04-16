# server/command_map.py
import logging
from typing import Dict, Any, Optional, List

# Import the shared protocol definition and server components
try:
    from shared.protocols import Command, encode_sysex # Need Command IDs
    from server.midi_bridge import MidiBridge
    from server.feedback_handler import FeedbackHandler
except ImportError:
    # Define dummy Command class if import fails during standalone testing
    class Command:
        GET_CHANNEL_NAMES=0; GET_CHANNEL_NAME_BY_INDEX=1; SET_CHANNEL_COLOR=2; RANDOMIZE_COLORS=3;
        TRANSPORT_CONTROL=4; SET_MIXER_LEVEL=5; GET_CHANNEL_COUNT=6; IS_CHANNEL_SELECTED=7;
        SELECT_CHANNEL=8; GET_CHANNEL_VOLUME=9; SET_CHANNEL_VOLUME=10; GET_TEMPO=11; SET_TEMPO=12;
        GET_IS_PLAYING=13; SELECT_PATTERN=14; GET_CURRENT_PATTERN=15; ADD_AUDIO_EFFECT=16;
        GET_MIXER_TRACK_COUNT=17; GET_MIXER_LEVEL=18;
    class MidiBridge: pass # Dummy classes
    class FeedbackHandler: pass
    print("[Command Mapper Warning] Failed to import shared protocols or server components.")


logger = logging.getLogger('flstudio-mcp.mapper')

class CommandMapper:
    """
    Maps high-level function calls (from MCP tools) to specific SysEx commands,
    sends them via the MidiBridge, and waits for responses via FeedbackHandler.
    """
    def __init__(self, midi_bridge: MidiBridge, feedback_handler: FeedbackHandler):
        """
        Initializes the CommandMapper.

        Args:
            midi_bridge: An instance of MidiBridge for sending commands.
            feedback_handler: An instance of FeedbackHandler for managing responses.
        """
        self.bridge = midi_bridge
        self.feedback = feedback_handler

    def execute_command(self, command_id: int, params: Optional[Dict[str, Any]] = None, wait_for_feedback: bool = True, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Core function to encode, send a SysEx command, and optionally wait for a response.

        Args:
            command_id (int): The Command ID from shared.protocols.Command.
            params (Optional[Dict[str, Any]]): Data payload for the command.
            wait_for_feedback (bool): Whether to wait for a response from the device.
            timeout (Optional[float]): Custom timeout for this specific command wait.

        Returns:
            Dict[str, Any]: The response dictionary from the device, or a status dictionary
                          indicating success/error of sending or timeout.
        """
        if not self.bridge or not self.bridge.output_port:
             logger.error(f"Cannot execute command {hex(command_id)}: MIDI output port not available/initialized in bridge.")
             return {"status": "error", "message": "MIDI output port not available"}

        request_id: Optional[int] = None
        payload: Dict[str, Any] = params.copy() if params else {}

        # If feedback is expected, register the request and add the ID to the payload
        if wait_for_feedback:
             try:
                request_id = self.feedback.register_request()
                payload["request_id"] = request_id # Add request ID for correlation by device
                logger.debug(f"Executing command {hex(command_id)} with request ID {request_id}")
             except Exception as e:
                  logger.exception(f"Failed to register feedback request for command {hex(command_id)}: {e}")
                  return {"status": "error", "message": f"Failed to register feedback request: {e}"}
        else:
             logger.debug(f"Executing command {hex(command_id)} without waiting for feedback.")

        # Encode the command and payload into a SysEx message
        sysex_message = encode_sysex(command_id, payload)

        if not sysex_message:
            logger.error(f"Failed to encode SysEx for command {hex(command_id)} with payload {payload}")
            # If we registered a request, we need to handle its eventual timeout
            if request_id is not None:
                # Try to retrieve the expected timeout error message
                return self.feedback.wait_for_response(request_id, custom_timeout=0.01) or \
                       {"status": "error", "message": "Failed SysEx encoding & failed getting timeout response"}
            else:
                return {"status": "error", "message": "Failed to encode SysEx message"}

        # Send the SysEx message via the MIDI bridge
        if not self.bridge.send_sysex(sysex_message):
             logger.error(f"Failed to send SysEx via bridge for command {hex(command_id)}")
             if request_id is not None:
                # Try to retrieve the expected timeout error message
                return self.feedback.wait_for_response(request_id, custom_timeout=0.01) or \
                       {"status": "error", "message": "Failed sending SysEx & failed getting timeout response"}
             else:
                return {"status": "error", "message": "Failed to send SysEx message via MIDI bridge"}

        # If sent successfully and we are waiting for feedback
        if wait_for_feedback and request_id is not None:
            response = self.feedback.wait_for_response(request_id, custom_timeout=timeout)
            # wait_for_response includes status/error/timeout messages
            return response or {"status": "error", "message": "Response handler returned None unexpectedly"}
        else:
            # Command sent successfully, not waiting for feedback
            return {"status": "success", "message": f"Command {hex(command_id)} sent (no feedback requested)."}

    # --- Methods mapping high-level actions to specific execute_command calls ---
    # These correspond to the MCP tools defined in main.py

    # Channel Info
    def get_channel_count(self) -> Dict[str, Any]:
        logger.info("Mapping request: get_channel_count")
        return self.execute_command(Command.GET_CHANNEL_COUNT, wait_for_feedback=True)

    def get_channel_names(self) -> Dict[str, Any]:
         logger.info("Mapping request: get_channel_names")
         return self.execute_command(Command.GET_CHANNEL_NAMES, wait_for_feedback=True)

    def get_channel_name(self, index: int) -> Dict[str, Any]:
         logger.info(f"Mapping request: get_channel_name (index={index})")
         return self.execute_command(Command.GET_CHANNEL_NAME_BY_INDEX, {"index": index}, wait_for_feedback=True)

    def is_channel_selected(self, index: int) -> Dict[str, Any]:
        logger.info(f"Mapping request: is_channel_selected (index={index})")
        return self.execute_command(Command.IS_CHANNEL_SELECTED, {"index": index}, wait_for_feedback=True)

    # Channel Control
    def set_channel_color(self, index: int, color: int) -> Dict[str, Any]:
         logger.info(f"Mapping request: set_channel_color (index={index}, color={hex(color)})")
         # Send and wait for simple ACK/Error from device
         return self.execute_command(Command.SET_CHANNEL_COLOR, {"index": index, "color": color}, wait_for_feedback=True)

    def select_channel(self, index: int, value: int = -1) -> Dict[str, Any]:
         logger.info(f"Mapping request: select_channel (index={index}, value={value})")
         return self.execute_command(Command.SELECT_CHANNEL, {"index": index, "value": value}, wait_for_feedback=True) # Wait for ACK

    def set_channel_volume(self, index: int, volume: float) -> Dict[str, Any]:
        logger.info(f"Mapping request: set_channel_volume (index={index}, volume={volume:.3f})")
        return self.execute_command(Command.SET_CHANNEL_VOLUME, {"index": index, "volume": volume}, wait_for_feedback=True) # Wait for ACK

    def set_channel_pan(self, index: int, pan: float) -> Dict[str, Any]:
        logger.info(f"Mapping request: set_channel_pan (index={index}, pan={pan:.3f})")
        return self.execute_command(Command.SET_CHANNEL_PAN, {"index": index, "pan": pan}, wait_for_feedback=True) # Wait for ACK

    def set_channel_mute(self, index: int, mute_state: bool) -> Dict[str, Any]:
        logger.info(f"Mapping request: set_channel_mute (index={index}, mute={mute_state})")
        return self.execute_command(Command.SET_CHANNEL_MUTE, {"index": index, "mute": mute_state}, wait_for_feedback=True) # Wait for ACK

    def set_channel_solo(self, index: int, solo_state: bool) -> Dict[str, Any]:
        logger.info(f"Mapping request: set_channel_solo (index={index}, solo={solo_state})")
        # Note: FL API might only support toggle for solo, adjust protocol if needed
        return self.execute_command(Command.SET_CHANNEL_SOLO, {"index": index, "solo": solo_state}, wait_for_feedback=True) # Wait for ACK


    # Visuals
    def randomize_channel_colors(self, selected_only: bool) -> Dict[str, Any]:
         logger.info(f"Mapping request: randomize_channel_colors (selected={selected_only})")
         return self.execute_command(Command.RANDOMIZE_COLORS, {"selected_only": selected_only}, wait_for_feedback=True) # Wait for ACK

    # Transport
    def control_transport(self, action: str) -> Dict[str, Any]:
         logger.info(f"Mapping request: control_transport ({action})")
         # Transport actions might return the new state in feedback
         return self.execute_command(Command.TRANSPORT_CONTROL, {"action": action.lower()}, wait_for_feedback=True)

    def get_is_playing(self) -> Dict[str, Any]:
         logger.info("Mapping request: get_is_playing")
         return self.execute_command(Command.GET_IS_PLAYING, wait_for_feedback=True)

    def set_tempo(self, bpm: float) -> Dict[str, Any]:
        logger.info(f"Mapping request: set_tempo (bpm={bpm})")
        return self.execute_command(Command.SET_TEMPO, {"bpm": bpm}, wait_for_feedback=True) # Wait for ACK/actual tempo

    def get_tempo(self) -> Dict[str, Any]:
        logger.info("Mapping request: get_tempo")
        return self.execute_command(Command.GET_TEMPO, wait_for_feedback=True)

    def select_pattern(self, pattern_number: int) -> Dict[str, Any]:
         logger.info(f"Mapping request: select_pattern (pattern={pattern_number})")
         return self.execute_command(Command.SELECT_PATTERN, {"pattern": pattern_number}, wait_for_feedback=True) # Wait for ACK

    def get_current_pattern(self) -> Dict[str, Any]:
         logger.info("Mapping request: get_current_pattern")
         return self.execute_command(Command.GET_CURRENT_PATTERN, wait_for_feedback=True)


    # Mixer
    def get_mixer_track_count(self) -> Dict[str, Any]:
         logger.info("Mapping request: get_mixer_track_count")
         return self.execute_command(Command.GET_MIXER_TRACK_COUNT, wait_for_feedback=True)

    def get_mixer_level(self, track_index: int) -> Dict[str, Any]:
         logger.info(f"Mapping request: get_mixer_level (track={track_index})")
         return self.execute_command(Command.GET_MIXER_LEVEL, {"track": track_index}, wait_for_feedback=True)

    def set_mixer_level(self, track_index: int, level: float) -> Dict[str, Any]:
         logger.info(f"Mapping request: set_mixer_level (track={track_index}, level={level:.3f})")
         return self.execute_command(Command.SET_MIXER_LEVEL, {"track": track_index, "level": level}, wait_for_feedback=True) # Wait for ACK

    # Effects
    def add_audio_effect(self, track_index: int, effect_identifier: str) -> Dict[str, Any]:
         logger.info(f"Mapping request: add_audio_effect (track={track_index}, effect='{effect_identifier}')")
         # Send effect name/ID, device script handles finding and loading
         return self.execute_command(Command.ADD_AUDIO_EFFECT, {"track": track_index, "effect": effect_identifier}, wait_for_feedback=True) # Wait for success/fail/slot


    # --- Add mappings for all other commands defined in shared.protocols.Command ---