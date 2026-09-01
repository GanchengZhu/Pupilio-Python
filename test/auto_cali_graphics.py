import time
from pupilio.cali_graphics import CalibrationUI

class AutoCalibrationUI(CalibrationUI):
    """
    An automated version of CalibrationUI for testing version compatibility.
    It simulates user inputs automatically so that tests do not hang waiting for key presses.
    """
    def __init__(self, pupil_io, ui_backend):
        super().__init__(pupil_io, ui_backend)
        self._auto_action_timer = time.time()
        
        # We override the UI backend's check_action to provide automatic 'continue'
        self._original_check_action = self.ui.check_action
        self.ui.check_action = self._auto_check_action
        
    def _auto_check_action(self):
        # Always read real events to keep the window responsive, but ignore them
        self._original_check_action()
        
        # Fire a 'continue' every 0.1 seconds to fast-forward through instruction screens
        if time.time() - self._auto_action_timer > 0.1:
            self._auto_action_timer = time.time()
            return 'continue'
        return None

    def draw(self, validate=False, bg_color=(255, 255, 255), hands_free=False):
        # Force hands_free to false so it relies on our auto 'continue' actions instead of waiting 11s
        super().draw(validate=validate, bg_color=bg_color, hands_free=False)
        
        # Restore original function just in case
        self.ui.check_action = self._original_check_action
