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
# End-to-end smoke tests that boot the SDK through both supported UI backends
# (Pygame and PsychoPy) by executing the bundled picture_viewing examples.
#
# These tests run against the simulation tracker backend so they do not require
# physical hardware in CI. The interactive parts of the flow are substituted:
# ``Pupilio.calibration_draw`` is replaced with a headless ``AutoCalibrationUI``,
# and the backend event loops are scripted so the examples advance without a human
# operator.
#
# Passing means the SDK's initialization path plus the example scripts'
# public API usage still work end to end across UI backends.

# Author: GC Zhu
# Email: zhugc2016@gmail.com

import os
import runpy
import sys
import unittest
from unittest.mock import patch

import pygame

# Directory containing the example scripts under test.
_EXAMPLE_SUBDIR = os.path.join('example', 'picture_viewing')


class _ExampleTestBase(unittest.TestCase):
    """
    Shared setup for tests that run an example script from ``example/picture_viewing``.

    Handles the two pieces of state the example scripts rely on: ``sys.path`` entries so
    imports resolve, and the process working directory so asset loads succeed. Both are
    restored in :meth:`tearDown` so running this suite does not affect unrelated tests.
    """

    def setUp(self):
        # Paths we add to sys.path; restored in tearDown.
        self._added_paths = []

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.example_dir = os.path.abspath(os.path.join(project_root, _EXAMPLE_SUBDIR))

        # Skip (rather than fail) when examples aren't shipped — e.g. running from a
        # wheel that excludes the example/ tree.
        if not os.path.isdir(self.example_dir):
            self.skipTest(f"example directory not found: {self.example_dir}")

        for path in (project_root, os.path.dirname(__file__), self.example_dir):
            if path not in sys.path:
                sys.path.insert(0, path)
                self._added_paths.append(path)

        # Saved so tearDown can restore it regardless of how the test exits.
        self._original_cwd = None

    def tearDown(self):
        if self._original_cwd is not None:
            os.chdir(self._original_cwd)

        for path in self._added_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                # Already removed (unlikely, but harmless).
                pass

    def _run_example(self, script_name):
        """
        chdir into the example directory and execute ``script_name`` via runpy.

        The example scripts load assets relative to the CWD, so changing directory is
        required. Restoration happens in tearDown rather than in a finally block here
        because we want it to run even if setUp partially succeeded.
        """
        self._original_cwd = os.getcwd()
        os.chdir(self.example_dir)
        try:
            runpy.run_path(script_name)
        finally:
            os.chdir(self._original_cwd)
            self._original_cwd = None


class TestPygameExample(_ExampleTestBase):
    """
    Smoke-test the Pygame example script end to end against the real tracker.

    Scripts the pygame event loop with a constant Enter keypress so the example's
    phase machine advances without user input, and neutralises ``pygame.time.wait``
    so the whole run completes in milliseconds.
    """

    def test_pygame_example(self):
        from pupilio import Pupilio
        from pupilio.ui_backend import PyGameUIBackend
        from auto_cali_graphics import AutoCalibrationUI

        # Signature MUST match Pupilio.calibration_draw's real parameter order:
        #     (self, screen=None, validate=False, bg_color=(255, 255, 255), hands_free=False)
        # so positional calls from the example bind the same way they would in production.
        def mock_calibration_draw(self_obj, screen=None, validate=False,
                                  bg_color=(255, 255, 255), hands_free=False):
            ui_backend = PyGameUIBackend(screen)
            cali_ui = AutoCalibrationUI(self_obj, ui_backend)
            cali_ui.draw(validate=validate, bg_color=bg_color, hands_free=hands_free)

        orig_init = Pupilio.__init__
        def mock_init(self_obj, config=None):
            if config is None:
                from pupilio import DefaultConfig
                config = DefaultConfig()
            config.simulation_mode = True
            orig_init(self_obj, config)

        def mock_event_get():
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)]

        with patch.object(Pupilio, '__init__', mock_init), \
             patch.object(Pupilio, 'calibration_draw', mock_calibration_draw), \
             patch('pygame.event.get', side_effect=mock_event_get), \
             patch('pygame.time.wait', return_value=None):
            self._run_example('picture_viewing_pygame.py')


class TestPsychoPyExample(_ExampleTestBase):
    """
    Smoke-test the PsychoPy example script end to end against the simulation tracker.

    Skipped when PsychoPy is not installed. Scripts ``psychopy.event.getKeys`` with a
    constant Enter keypress and neutralises ``psychopy.core.wait`` so the run does not
    block on real time. A clean ``SystemExit(0)`` (PsychoPy's usual way to close the
    window) is treated as success; any non-zero exit code is re-raised.
    """

    def setUp(self):
        super().setUp()

        try:
            import psychopy  # noqa: F401
        except ImportError:
            self.skipTest("psychopy is not installed")

    def test_psychopy_example(self):
        from pupilio import Pupilio
        from pupilio.ui_backend import PsychoPyUIBackend
        from auto_cali_graphics import AutoCalibrationUI

        # Same signature contract as the Pygame mock above.
        def mock_calibration_draw(self_obj, screen=None, validate=False,
                                  bg_color=(255, 255, 255), hands_free=False):
            ui_backend = PsychoPyUIBackend(screen)
            cali_ui = AutoCalibrationUI(self_obj, ui_backend)
            cali_ui.draw(validate=validate, bg_color=bg_color, hands_free=hands_free)

        orig_init = Pupilio.__init__
        def mock_init(self_obj, config=None):
            if config is None:
                from pupilio import DefaultConfig
                config = DefaultConfig()
            config.simulation_mode = True
            orig_init(self_obj, config)

        def mock_getKeys(*args, **kwargs):
            return ['return']

        with patch.object(Pupilio, '__init__', mock_init), \
             patch.object(Pupilio, 'calibration_draw', mock_calibration_draw), \
             patch('psychopy.event.getKeys', side_effect=mock_getKeys), \
             patch('psychopy.core.wait', return_value=None):
            try:
                self._run_example('picture_viewing_psychopy.py')
            except SystemExit as exc:
                # psychopy.core.quit() raises SystemExit(0); treat as success.
                if exc.code not in (0, None):
                    raise

if __name__ == '__main__':
    unittest.main()

