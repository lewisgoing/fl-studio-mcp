# server/feedback_handler.py
import queue
import threading
import time
import logging
from typing import Dict, Any, Optional

# Import the shared protocol definition
try:
    from shared.protocols import decode_sysex, Command
except ImportError:
    # Define dummy Command class if import fails during standalone testing
    class Command: RESPONSE_SUCCESS = 0x70; RESPONSE_ERROR = 0x71; ASYNC_UPDATE = 0x7F
    def decode_sysex(msg): return None
    print("[Feedback Handler Warning] Failed to import shared protocols.")


logger = logging.getLogger('flstudio-mcp.feedback')

class FeedbackHandler:
    """
    Handles incoming SysEx feedback, correlates responses to requests using IDs,
    and provides a mechanism to wait for specific responses.
    """
    def __init__(self, timeout: float = 5.0):
        """
        Initializes the FeedbackHandler.

        Args:
            timeout (float): Default time in seconds to wait for a response.
        """
        # Dictionary to store pending request IDs and their corresponding threading Events
        self._pending_requests: Dict[int, threading.Event] = {}
        # Dictionary to store received response data, keyed by request ID
        self._responses: Dict[int, Any] = {}
        # Lock for thread-safe access to shared dictionaries
        self._lock = threading.Lock()
        # Simple counter for generating unique request IDs
        self._request_counter: int = 0
        # Default timeout for waiting for responses
        self.timeout: float = timeout
        # Queue for unsolicited messages (errors, async updates) from the device
        self.unsolicited_queue = queue.Queue()

    def _generate_request_id(self) -> int:
        """Generates a sequential, unique ID for a request."""
        with self._lock:
            self._request_counter = (self._request_counter + 1) % 0xFFFF # Keep within 16 bits
            # Avoid using 0 if possible, might be ambiguous in some protocols
            if self._request_counter == 0:
                self._request_counter = 1
            # Ensure the ID isn't currently pending (highly unlikely with sequential IDs)
            while self._request_counter in self._pending_requests:
                 self._request_counter = (self._request_counter + 1) % 0xFFFF
                 if self._request_counter == 0: self._request_counter = 1
            return self._request_counter

    def register_request(self) -> int:
        """
        Registers an outgoing request that expects a response.
        Creates a unique request ID and an associated event to wait on.

        Returns:
            int: The unique request ID generated for this request.
        """
        request_id = self._generate_request_id()
        event = threading.Event()
        with self._lock:
            self._pending_requests[request_id] = event
            # Clear any potentially stale response for this ID (shouldn't happen with counter)
            if request_id in self._responses:
                 del self._responses[request_id]
        logger.debug(f"Registered request expecting response. ID: {request_id}")
        return request_id

    def wait_for_response(self, request_id: int, custom_timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Waits for a specific duration for a response corresponding to the given request ID.

        Args:
            request_id (int): The ID of the request whose response is awaited.
            custom_timeout (Optional[float]): Override the default timeout for this specific wait.

        Returns:
            Optional[Dict[str, Any]]: The received response data dictionary,
                                      or a dictionary with status='error' on timeout/error.
                                      Returns None only if the request ID was invalid.
        """
        event = None
        with self._lock:
            # Retrieve the event associated with the request ID
            event = self._pending_requests.get(request_id)

        if not event:
            logger.error(f"Attempted to wait for an unregistered or already completed request ID: {request_id}")
            # Indicate clearly that the ID wasn't valid for waiting
            return {"status": "error", "message": f"Invalid or completed request ID: {request_id}"}

        wait_duration = custom_timeout if custom_timeout is not None else self.timeout
        logger.debug(f"Waiting ({wait_duration:.1f}s) for response to request ID: {request_id}")

        # Wait for the event to be set (by handle_sysex_message) or timeout
        event_was_set = event.wait(timeout=wait_duration)

        # --- Cleanup and Response Retrieval (Thread-Safe) ---
        response_payload = None
        cleanup_needed = False
        with self._lock:
            # Check if the request is still pending *after* the wait
            if request_id in self._pending_requests:
                del self._pending_requests[request_id] # Remove event from pending
                cleanup_needed = True # Mark that we removed it

            if event_was_set:
                # Event was set, response should be in _responses
                response_payload = self._responses.pop(request_id, None) # Retrieve and remove response
                if response_payload:
                    logger.info(f"Received response for ID {request_id}: {response_payload}")
                else:
                    # This indicates a logic error: event was set, but no response data was stored.
                    logger.error(f"Internal Error: Event set for ID {request_id}, but no response data found!")
                    response_payload = {"status": "error", "message": "Internal error: Event set but no response found"}
            else:
                # Timeout occurred
                logger.warning(f"Timeout waiting for response to request ID: {request_id}")
                response_payload = {"status": "error", "message": f"Timeout waiting for feedback (ID: {request_id})"}

        # Log cleanup action
        if cleanup_needed:
             logger.debug(f"Cleaned up pending request ID: {request_id}")

        return response_payload


    def handle_sysex_message(self, raw_sysex: bytes):
        """
        Decodes incoming raw SysEx bytes and routes the message.
        If it's a response to a pending request, it stores the data and signals the waiting thread.
        If it's an unsolicited message (error, update), it places it in the unsolicited_queue.
        """
        decoded = decode_sysex(raw_sysex)
        if not decoded:
            logger.warning(f"Failed to decode incoming SysEx: {raw_sysex.hex()}")
            # Put raw undecoded message in error queue? Or just log?
            try:
                self.unsolicited_queue.put({"status": "error", "message": "Failed SysEx decode", "raw_hex": raw_sysex.hex()})
            except Exception as e:
                 logger.error(f"Error putting undecoded message into queue: {e}")
            return

        command_id = decoded.get("command_id")
        # Ensure data is always a dict, even if decoding yielded None or non-dict
        data = decoded.get("data") if isinstance(decoded.get("data"), dict) else {}
        response_id = data.get("response_to") if isinstance(data, dict) else None # Check if response is linked to a request

        logger.debug(f"Handling decoded SysEx: Cmd={hex(command_id)}, Data={data}, ResponseID={response_id}")

        # --- Route based on Command ID and Response ID ---
        is_response_command = (command_id == Command.RESPONSE_SUCCESS or command_id == Command.RESPONSE_ERROR)

        if is_response_command and response_id is not None:
            # This is a direct response to a specific request we sent
            event = None
            with self._lock:
                event = self._pending_requests.get(response_id) # Check if we are waiting for this ID
                if event:
                    # Store the response data (excluding the response_to ID itself)
                    response_payload = data.copy()
                    response_payload.pop("response_to", None)
                    # Add a status field based on the response command ID
                    response_payload["status"] = "success" if command_id == Command.RESPONSE_SUCCESS else "error"
                    self._responses[response_id] = response_payload
                    logger.debug(f"Stored response for ID {response_id}. Payload: {response_payload}")
                else:
                    # Received a response for an ID we are no longer waiting for (or never registered)
                     logger.warning(f"Received response for unknown, timed out, or completed request ID: {response_id}. Discarding.")
            # Signal the waiting thread *outside* the lock if the event was found
            if event:
                event.set()
                logger.debug(f"Signalled event for response ID {response_id}.")

        elif command_id == Command.ASYNC_UPDATE:
            # Handle unsolicited updates from FL Studio (e.g., tempo changes, playback state)
            logger.info(f"Received Async Update from FL Studio: {data}")
            try:
                self.unsolicited_queue.put(decoded) # Put the full decoded message in the queue
            except Exception as e:
                 logger.error(f"Error putting async update into queue: {e}")

        else:
            # Received an unexpected command ID from the device, or a response without an ID
            if is_response_command:
                 logger.warning(f"Received unsolicited response (Cmd={hex(command_id)}) without response ID: {data}. Treating as error/update.")
            else:
                 logger.warning(f"Received unexpected SysEx command ID from device: {hex(command_id)}. Data: {data}. Treating as error/update.")
            try:
                # Add an error status if not already present
                if "status" not in data: data["status"] = "error"
                if "message" not in data: data["message"] = f"Unexpected command {hex(command_id)}"
                self.unsolicited_queue.put({"command_id": command_id, "data": data})
            except Exception as e:
                 logger.error(f"Error putting unexpected message into queue: {e}")

    def get_unsolicited_message(self, block=False, timeout=None) -> Optional[Dict[str, Any]]:
        """Retrieves the next unsolicited message from the queue."""
        try:
            return self.unsolicited_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            logger.exception(f"Error getting message from unsolicited queue: {e}")
            return None