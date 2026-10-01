# _*_ coding: utf-8 _*_
# Copyright (c) 2024, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by  Hangzhou DeepGaze Science and Technology Co., Ltd licencees only.
# Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of  Hangzhou DeepGaze Science and Technology Co., Ltd nor the name of
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
# IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# DESCRIPTION:
# Test-only shim that exposes CalibrationUI under the name the smoke tests
# import. It intentionally adds no behaviour: input scripting is handled by the
# tests themselves (via patches on the backend's event loop), so overriding
# ``ui.check_action`` here would bypass that scripting and stall the flow.

# Author: GC Zhu
# Email: zhugc2016@gmail.com

from pupilio.cali_graphics import CalibrationUI


class AutoCalibrationUI(CalibrationUI):
    """
    Alias for :class:`~pupilio.cali_graphics.CalibrationUI`.

    Exists only so the smoke tests can keep importing ``AutoCalibrationUI`` from
    ``auto_cali_graphics`` without changing test code.

    This class deliberately overrides nothing:

    * ``__init__`` — the old version replaced ``self.ui.check_action`` with an
      auto-advancing stub, which shadowed the backend's real event handling.
    * ``draw`` — the old version forced ``hands_free=False`` and restored the
      patched ``check_action`` afterwards, both no longer necessary.
    * ``check_action`` — scripting is done at the test level via
      ``patch('pygame.event.get', ...)`` and
      ``patch('psychopy.event.getKeys', ...)``, so any override here would fight
      with the test's mocks.

    If you need automated input for an interactive demo, subclass this or
    ``CalibrationUI`` directly and override ``draw`` / ``check_action`` in your
    subclass — do not add behaviour here, because the smoke tests rely on this
    class being a pure pass-through.
    """


# class AutoCalibrationUI(CalibrationUI):
#     """
#     An automated version of CalibrationUI for testing version compatibility.
#     It simulates user inputs automatically so that tests do not hang waiting for key presses.
#     """
#     def __init__(self, pupil_io, ui_backend):
#         super().__init__(pupil_io, ui_backend)
#         self._auto_action_timer = time.time()
#
#         # We override the UI backend's check_action to provide automatic 'continue'
#         self._original_check_action = self.ui.check_action
#         self.ui.check_action = self._auto_check_action
#
#     def _auto_check_action(self):
#         # Always read real events to keep the window responsive, but ignore them
#         self._original_check_action()
#
#         # Fire a 'continue' every 0.1 seconds to fast-forward through instruction screens
#         if time.time() - self._auto_action_timer > 0.1:
#             self._auto_action_timer = time.time()
#             return 'continue'
#         return None
#
#     def draw(self, validate=False, bg_color=(255, 255, 255), hands_free=False):
#         # Force hands_free to false so it relies on our auto 'continue' actions instead of waiting 11s
#         super().draw(validate=validate, bg_color=bg_color, hands_free=False)
#
#         # Restore original function just in case
#         self.ui.check_action = self._original_check_action
