"""
Testing module for FL Studio MCP Controller
"""

import channels
import time
import random

class TestSuite:
    """Test suite for FL Studio MCP Controller helper functions"""
    
    def __init__(self, channel_helpers):
        """Initialize test suite with channel helper functions
        
        Args:
            channel_helpers: Module containing channel helper functions
        """
        self.helpers = channel_helpers
    
    def _print_status(self, test_name, success, manual_check_msg=""):
        """Prints the formatted status of a test."""
        status_icon = "✅" if success else "❌"
        status_text = "PASSED" if success else "FAILED"
        print(f"--- {status_icon} Result: {test_name} {status_text} ---")
        if manual_check_msg:
            print(f"  ➡️ {manual_check_msg}")
        print("") # Add a newline for spacing

    # --- Individual Test Functions ---

    def test_getChannelCount(self):
        test_name = "Get Channel Count (Group)"
        print(f"--- Testing: {test_name} ---")
        passed = False
        manual_check = "Manually verify the reported count matches the visible channels in the current group."
        try:
            count = self.helpers.getChannelCount()
            print(f"  Reported count: {count}")
            if count > 0: # Basic sanity check
                passed = True
            else:
                print("  [Assertion Fail] Expected at least one channel.")
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        self._print_status(test_name, passed, manual_check)
        return passed

    def test_getSelectedChannelIndices(self):
        test_name = "Get Selected Channel Indices"
        print(f"--- Testing: {test_name} ---")
        passed = False
        # !!! SETUP: Manually select channels 1 and 3 before running !!!
        expected_indices = [1, 3] 
        manual_check = f"Manually ensure channels {expected_indices} (and only those) were selected before running."
        try:
            indices = self.helpers.getAllSelectedChannelIndices()
            print(f"  Reported selected indices: {indices}")
            if indices == expected_indices:
                passed = True
            else:
                print(f"  [Assertion Fail] Expected {expected_indices}, got {indices}.")
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        self._print_status(test_name, passed, manual_check)
        return passed
        
    def test_selectSingleChannel(self):
        test_name = "Select Single Channel"
        print(f"--- Testing: {test_name} ---")
        passed = False
        test_index = 0
        manual_check = f"Visually confirm ONLY channel {test_index} is selected in the Channel Rack."
        try:
            print(f"  Selecting single channel: {test_index}")
            self.helpers.selectSingleChannel(test_index)
            time.sleep(0.1) # UI update delay
            
            # Verification
            if self.helpers.isChannelSelected(test_index) and not self.helpers.isChannelSelected(1): # Check target is selected, another is not
                 passed = True
            else:
                 print("  [Assertion Fail] Selection state after selectSingleChannel is not as expected.")
                 
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        self._print_status(test_name, passed, manual_check)
        # Clean up: deselect all for potential next tests
        self.helpers.deselectAllChannels() 
        return passed

    def test_selectAllDeselectAll(self):
        test_name = "Select All / Deselect All"
        print(f"--- Testing: {test_name} ---")
        passed = True # Assume pass unless specific check fails
        manual_check = "Visually confirm selection changes as described in the log."
        try:
            print("  Selecting all channels...")
            self.helpers.selectAllChannels()
            time.sleep(0.1)
            # Basic check: is first channel selected? (Assuming > 0 channels)
            if not self.helpers.isChannelSelected(0):
                 passed = False
                 print("  [Assertion Fail] Channel 0 not selected after selectAll.")
            print("  ➡️ Visually confirm ALL channels selected.")
            
            print("  Deselecting all channels...")
            self.helpers.deselectAllChannels()
            time.sleep(0.1)
            # Basic check: is first channel deselected?
            if self.helpers.isChannelSelected(0):
                 passed = False
                 print("  [Assertion Fail] Channel 0 still selected after deselectAll.")
            print("  ➡️ Visually confirm NO channels selected.")

        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        self._print_status(test_name, passed, manual_check)
        return passed

    def test_setGetChannelName(self):
        test_name = "Set/Get Channel Name"
        print(f"--- Testing: {test_name} ---")
        passed = False
        test_index = 1 # Assume channel 1 exists
        original_name = "[Unknown]"
        manual_check = ""
        try:
            original_name = self.helpers.getChannelName(test_index)
            print(f"  Initial name for channel {test_index}: '{original_name}'")
            
            new_name = f"Test_{random.randint(100, 999)}"
            print(f"  Setting name for channel {test_index} to '{new_name}'...")
            self.helpers.setChannelName(test_index, new_name)
            time.sleep(0.1) 

            read_name = self.helpers.getChannelName(test_index)
            print(f"  Name read back: '{read_name}'")
            
            if read_name == new_name:
                passed = True
            else:
                print(f"  [Assertion Fail] Read name '{read_name}' doesn't match set name '{new_name}'.")
            
            manual_check = f"Visually confirm channel {test_index}'s name is '{new_name}' in FL Studio."

        except Exception as e:
            print(f"  [ERROR] Exception during test: {e}")
            passed = False
        finally:
            # Attempt to restore original name (optional)
            if original_name != "[Unknown]":
                 self.helpers.setChannelName(test_index, original_name)
                 
        self._print_status(test_name, passed, manual_check)
        return passed

    def test_setGetChannelColor(self):
        test_name = "Set/Get Channel Color"
        print(f"--- Testing: {test_name} ---")
        passed = False
        test_index = 1 # Assume channel 1 exists
        original_color = 0
        manual_check = ""
        try:
            original_color = self.helpers.getChannelColor(test_index)
            print(f"  Initial color for channel {test_index}: {hex(original_color)}")
            
            test_color = 0xFF8000 # Orange (BBGGRR)
            print(f"  Setting color for channel {test_index} to Orange ({hex(test_color)})...")
            self.helpers.setChannelColor(test_index, test_color)
            time.sleep(0.1) 

            read_color = self.helpers.getChannelColor(test_index)
            print(f"  Color read back: {hex(read_color)}")
            
            # FL Studio might slightly adjust colors, check if close
            if abs(read_color - test_color) > 0x050505: # Allow some tolerance
                 passed = False
                 print(f"  [Assertion Fail] Read color {hex(read_color)} doesn't match set color {hex(test_color)} closely.")
            else:
                 passed = True # Passed automated check
            
            manual_check = f"Visually confirm channel {test_index} is Orange in FL Studio."

        except Exception as e:
            print(f"  [ERROR] Exception during test: {e}")
            passed = False
        finally:
            # Attempt to restore original color (optional)
             self.helpers.setChannelColor(test_index, original_color)
             
        self._print_status(test_name, passed, manual_check)
        return passed

    def test_setSelectedChannelsColor(self):
        test_name = "Set Selected Channels Color (Bulk)"
        print(f"--- Testing: {test_name} ---")
        passed = True # Assume pass if code runs, rely on manual check
        # !!! SETUP: Manually select channels 1 and 3 before running !!!
        selected_indices = [1, 3] 
        test_color = 0x00FFFF # Cyan (BBGGRR)
        manual_check = f"Visually confirm channels {selected_indices} are now Cyan."
        try:
            print(f"  Setting color of selected channels ({selected_indices}) to Cyan ({hex(test_color)})...")
            self.helpers.setSelectedChannelsColor(test_color)
            time.sleep(0.1)
            
            # Optional: Add checks for individual channel colors here if desired
            
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        self._print_status(test_name, passed, manual_check)
        # Clean up: Deselect channels? Reset colors? (complex)
        return passed
        
    def test_toggleSetMute(self):
        test_name = "Toggle/Set Channel Mute"
        print(f"--- Testing: {test_name} ---")
        passed = True
        test_index = 0 # Use channel 0
        manual_check = "Visually/Audibly confirm mute state changes for channel 0 as described."
        try:
            initial_mute = self.helpers.isChannelMuted(test_index)
            print(f"  Initial mute state for channel {test_index}: {initial_mute}")

            print(f"  Toggling mute...")
            self.helpers.toggleChannelMute(test_index)
            time.sleep(0.1)
            toggled_mute = self.helpers.isChannelMuted(test_index)
            if toggled_mute == initial_mute:
                passed = False
                print(f"  [Assertion Fail] Mute state {toggled_mute} did not change after toggle.")
            print(f"  Mute state after toggle: {toggled_mute}")

            print(f"  Setting mute to True...")
            self.helpers.setChannelMute(test_index, True)
            time.sleep(0.1)
            if not self.helpers.isChannelMuted(test_index):
                passed = False
                print(f"  [Assertion Fail] Mute state is not True after setChannelMute(True).")
            
            print(f"  Setting mute to False...")
            self.helpers.setChannelMute(test_index, False)
            time.sleep(0.1)
            if self.helpers.isChannelMuted(test_index):
                 passed = False
                 print(f"  [Assertion Fail] Mute state is not False after setChannelMute(False).")

        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        self._print_status(test_name, passed, manual_check)
        return passed

    def test_setGetVolume(self):
        test_name = "Set/Get Channel Volume"
        print(f"--- Testing: {test_name} ---")
        passed = False
        test_index = 0 # Use channel 0
        original_volume = 0.0
        manual_check = ""
        try:
            original_volume = self.helpers.getChannelVolume(test_index)
            print(f"  Initial volume for channel {test_index}: {original_volume:.3f}")

            test_volume = 0.25 # 25%
            print(f"  Setting volume for channel {test_index} to {test_volume}...")
            self.helpers.setChannelVolume(test_index, test_volume)
            time.sleep(0.1)

            read_volume = self.helpers.getChannelVolume(test_index)
            print(f"  Volume read back: {read_volume:.3f}")
            
            # Compare with tolerance
            if abs(read_volume - test_volume) < 0.01:
                 passed = True
            else:
                 print(f"  [Assertion Fail] Read volume {read_volume:.3f} doesn't match set volume {test_volume} closely.")

            manual_check = f"Visually/Audibly confirm volume of channel {test_index} is low (~25%)."

        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            passed = False
        finally:
            # Attempt to restore original volume
             self.helpers.setChannelVolume(test_index, original_volume)
             
        self._print_status(test_name, passed, manual_check)
        return passed

    # --- Main Test Runner ---
    def run_all_tests(self):
        """Runs all individual channel helper tests and reports summary."""
        print("="*20 + " Starting Channel Helper Test Suite " + "="*20)
        print(f"Timestamp: {time.ctime()}")
        
        # !!! REMINDER: Manually set up FL Studio project before running! !!!
        # (e.g., 5+ channels, initially select channels 1 and 3)
        print("Starting Channel Helper Test Suite...")

        test_functions = [
            self.test_getChannelCount,
            self.test_getSelectedChannelIndices,
            self.test_selectSingleChannel,
            self.test_selectAllDeselectAll,
            self.test_setGetChannelName,
            self.test_setGetChannelColor,
            self.test_setSelectedChannelsColor,
            self.test_toggleSetMute,
            self.test_setGetVolume,
        ]

        results = {"passed": 0, "failed": 0, "total": 0}

        for test_func in test_functions:
            # Small delay between tests can sometimes help UI catch up
            time.sleep(0.3) 
            results["total"] += 1
            if test_func(): # Call the individual test function
                results["passed"] += 1
            else:
                results["failed"] += 1
                
        # --- Summary ---
        print("\n" + "="*20 + " Test Suite Summary " + "="*20)
        print(f"Total Tests Run: {results['total']}")
        print(f"✅ Passed:        {results['passed']}")
        print(f"❌ Failed:        {results['failed']}")
        print("="*56)
        
        return results 