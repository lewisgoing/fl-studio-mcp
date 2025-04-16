# server/midi_bridge.py
import mido
import mido.backends.rtmidi # Explicitly import backend if needed
import time
import logging
import threading
from typing import Optional, List, Callable, Set

logger = logging.getLogger('flstudio-mcp.bridge')

class MidiBridge:
    """Handles MIDI port discovery, opening, sending SysEx, and listening for SysEx."""

    def __init__(self, output_port_name_contains: str, input_port_name_contains: str, sysex_callback: Callable[[bytes], None]):
        """
        Initializes the MidiBridge.

        Args:
            output_port_name_contains: Substring to identify the desired MIDI output port.
            input_port_name_contains: Substring to identify the desired MIDI input port.
            sysex_callback: Function to call when a SysEx message is received on the input port.
        """
        self.output_port_name_contains = output_port_name_contains
        self.input_port_name_contains = input_port_name_contains
        self.sysex_callback = sysex_callback # Function to call when SysEx is received

        self.output_port: Optional[mido.ports.BaseOutput] = None
        self.input_port: Optional[mido.ports.BaseInput] = None
        self.output_port_name: Optional[str] = None
        self.input_port_name: Optional[str] = None

        self.listener_thread: Optional[threading.Thread] = None
        self.stop_listener_flag = threading.Event()

        self._find_ports() # Discover ports on initialization

    def _find_ports(self):
        """Attempts to find suitable MIDI input and output ports."""
        # --- Find Output Port ---
        try:
            available_outputs: List[str] = mido.get_output_names()
            logger.info(f"Available MIDI outputs: {available_outputs}")
            # Prioritize exact or substring match
            self.output_port_name = next((p for p in available_outputs if self.output_port_name_contains in p), None)

            # Fallback: If specific not found, try first 'IAC' not matching input target
            if not self.output_port_name:
                 logger.warning(f"Output port '{self.output_port_name_contains}' not found. Looking for fallback IAC port...")
                 self.output_port_name = next((p for p in available_outputs if 'IAC' in p and self.input_port_name_contains not in p), None)
                 if not self.output_port_name: # If still not found, take any IAC
                      self.output_port_name = next((p for p in available_outputs if 'IAC' in p), None)

            if self.output_port_name:
                logger.info(f"Selected MIDI output port: {self.output_port_name}")
                # Try opening the port immediately to confirm access
                self.open_output()
            else:
                logger.error(f"Could not find suitable MIDI output port containing '{self.output_port_name_contains}' or any IAC fallback.")

        except Exception as e:
            logger.exception(f"Error finding MIDI output ports: {e}")


        # --- Find Input Port Name (don't open yet) ---
        try:
            available_inputs: List[str] = mido.get_input_names()
            logger.info(f"Available MIDI inputs: {available_inputs}")
            # Prioritize exact or substring match
            self.input_port_name = next((p for p in available_inputs if self.input_port_name_contains in p), None)

             # Fallback: If specific not found, try first 'IAC' not matching output target
            if not self.input_port_name:
                 logger.warning(f"Input port '{self.input_port_name_contains}' not found. Looking for fallback IAC port...")
                 self.input_port_name = next((p for p in available_inputs if 'IAC' in p and self.output_port_name_contains not in p), None)
                 if not self.input_port_name: # If still not found, take any IAC
                      self.input_port_name = next((p for p in available_inputs if 'IAC' in p), None)


            if self.input_port_name:
                logger.info(f"Selected MIDI input port for feedback: {self.input_port_name}")
            else:
                 logger.error(f"Could not find suitable MIDI input port containing '{self.input_port_name_contains}' or any IAC fallback. Feedback disabled.")
        except Exception as e:
             logger.exception(f"Error finding MIDI input ports: {e}")


    def open_output(self) -> bool:
         """Opens or reopens the selected output MIDI port."""
         if self.output_port and not self.output_port.closed:
             return True # Already open
         if not self.output_port_name:
             logger.error("Cannot open output port: No port name selected.")
             return False
         try:
             self.output_port = mido.open_output(self.output_port_name)
             logger.info(f"Opened MIDI output port: {self.output_port_name}")
             return True
         except Exception as e:
             logger.error(f"Failed to open output port '{self.output_port_name}': {e}")
             self.output_port = None
             return False

    def send_sysex(self, sysex_message: bytes) -> bool:
        """Sends a raw SysEx message byte string."""
        if not self.open_output(): # Ensure port is open before sending
             logger.error("Cannot send SysEx: Output port could not be opened.")
             return False
        if not self.output_port: # Should not happen if open_output succeeded
            logger.error("Cannot send SysEx: Output port object is None.")
            return False

        try:
            # Mido messages require the F0 and F7 bytes for SysEx
            if not sysex_message.startswith(b'\xF0') or not sysex_message.endswith(b'\xF7'):
                 logger.error("Invalid SysEx format: Missing F0 start or F7 end byte.")
                 return False

            # Sending raw bytes might require specific backend handling or mido.Message conversion
            # Using mido.Message.from_bytes is safer
            msg = mido.Message.from_bytes(sysex_message)
            self.output_port.send(msg)
            logger.debug(f"Sent SysEx ({len(sysex_message)} bytes): {sysex_message.hex()}")
            return True
        except mido.exceptions.PortNotOpenError:
             logger.error("Cannot send SysEx: PortNotOpenError. Attempting to reopen.")
             self.output_port = None # Force reopen on next call
             return False
        except ValueError as e:
             # Catch potential errors from from_bytes if message is malformed
             logger.error(f"Cannot send SysEx: Invalid message bytes. Error: {e}. Message(hex): {sysex_message.hex()}")
             return False
        except Exception as e:
            logger.exception(f"Unexpected error sending SysEx: {e}")
            # Consider closing/reopening port on certain errors
            # self.output_port.close()
            # self.output_port = None
            return False

    def _midi_listener_func(self):
        """Internal function executed in the listener thread."""
        if not self.input_port_name:
            logger.error("Listener thread cannot start: No input port name.")
            return

        logger.info(f"MIDI input listener thread starting for port: {self.input_port_name}...")
        retries = 5 # More retries for initial connection
        wait_time = 2
        open_success = False

        for attempt in range(retries):
            try:
                # Attempt to open the input port
                self.input_port = mido.open_input(self.input_port_name)
                logger.info(f"MIDI input listener successfully opened port: {self.input_port_name}")
                open_success = True
                break # Exit retry loop on success
            except Exception as e:
                logger.error(f"MIDI input listener failed to open port (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    logger.info(f"Retrying listener port opening in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("MIDI input listener failed to open port after multiple retries. Thread exiting.")
                    return # Stop the thread if port cannot be opened

        # If port opened, start listening loop
        while not self.stop_listener_flag.is_set() and self.input_port and not self.input_port.closed:
            try:
                # Use iter_pending for non-blocking checks
                for msg in self.input_port.iter_pending():
                    if msg.type == 'sysex':
                        logger.debug(f"Bridge received SysEx ({len(msg.bytes)} bytes): {msg.hex()}")
                        try:
                             self.sysex_callback(msg.bytes()) # Pass raw bytes to the feedback handler
                        except Exception as e:
                             logger.exception("Error in sysex_callback function.")
                    # else: logger.debug(f"Bridge received other MIDI: {msg}") # Optional logging

                # Prevent busy-waiting
                time.sleep(0.02) # Sleep briefly (e.g., 20ms)

            except mido.exceptions.PortNotOpenError:
                 logger.error("MIDI input port closed unexpectedly. Attempting to reopen...")
                 if self.input_port and not self.input_port.closed: self.input_port.close()
                 self.input_port = None
                 open_success = False
                 # Re-enter the opening retry loop
                 for attempt in range(retries):
                      # Wait longer between reopen attempts
                      time.sleep(wait_time * (attempt + 1))
                      try:
                           self.input_port = mido.open_input(self.input_port_name)
                           logger.info(f"MIDI input listener re-opened port: {self.input_port_name}")
                           open_success = True
                           break
                      except Exception as e:
                           logger.error(f"Failed to reopen input port (attempt {attempt + 1}): {e}")
                 if not open_success:
                      logger.error("Failed to reopen input port after errors. Listener thread stopping.")
                      self.stop_listener_flag.set() # Signal exit

            except Exception as e:
                logger.exception("Unexpected error in MIDI listener loop. Stopping listener.")
                self.stop_listener_flag.set() # Signal exit on other errors

        # --- Cleanup after loop exit ---
        logger.info("MIDI input listener thread loop finished.")
        if self.input_port and not self.input_port.closed:
            logger.info("Closing input port in listener finally block.")
            try:
                self.input_port.close()
            except Exception as e:
                 logger.error(f"Error closing input port during listener cleanup: {e}")
        self.input_port = None
        logger.info("MIDI input listener thread stopped.")


    def start_listener(self):
        """Starts the MIDI listener thread if not already running."""
        if not self.input_port_name:
            logger.warning("Cannot start listener: No input port name found/selected.")
            return
        if self.listener_thread is None or not self.listener_thread.is_alive():
            self.stop_listener_flag.clear()
            self.listener_thread = threading.Thread(target=self._midi_listener_func, name="MidiListenerThread", daemon=True)
            self.listener_thread.start()
        else:
            logger.info("Listener thread already running.")

    def stop_listener(self):
        """Signals the MIDI listener thread to stop and waits for it to exit."""
        if self.listener_thread and self.listener_thread.is_alive():
            logger.info("Stopping MIDI listener thread...")
            self.stop_listener_flag.set()
            self.listener_thread.join(timeout=2.0) # Wait max 2 seconds
            if self.listener_thread.is_alive():
                logger.warning("MIDI Listener thread did not stop gracefully after timeout.")
            else:
                 logger.info("MIDI Listener thread stopped.")
            self.listener_thread = None
        else:
            logger.info("Listener thread was not running or already stopped.")
        # Port closing is handled within the thread's finally block

    def close_ports(self):
        """Closes all managed MIDI ports and stops the listener thread."""
        logger.info("Closing MIDI bridge ports and stopping listener...")
        self.stop_listener() # Ensure thread is stopped first
        if self.output_port and not self.output_port.closed:
            logger.info("Closing MIDI output port.")
            try:
                self.output_port.close()
            except Exception as e:
                 logger.error(f"Error closing output port: {e}")
        self.output_port = None
        # Input port should be closed by the listener thread stopping
        logger.info("MIDI bridge cleanup finished.")